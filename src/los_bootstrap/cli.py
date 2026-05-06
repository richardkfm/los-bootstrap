"""Command-line entry point for `los-bootstrap`.

Phase 1 commands:
    devices    list ADB-connected devices
    info       print device facts
    audit      run privacy/degoogle audit
    report     info + audit, text or --json
    recommend  print non-binding bootstrap recommendations
    version    print version

Phase 2 commands:
    profiles   list bundled profiles
    plan       dry-run a profile against the connected device
    apply      execute a profile (requires --confirm)

Phase 3 commands:
    harden     run hardening checks and (optionally) apply fixes interactively

Phase 4 commands:
    location   location stack diagnostics and app compatibility matrix
               location doctor  — diagnose the location stack on the connected device
               location compat  — show app location compatibility matrix (no device needed)

Phase 5 commands:
    camera     GCam port profiles and XML config guidance (no device needed)
               camera list-profiles  — list all known device GCam port profiles
               camera show <codename>  — show full profile for a device codename

Phase 8 commands:
    flash      ROM flashing assistant (bootloader unlock + sideload)
               flash status   — detect device state and manufacturer
               flash prepare  — manufacturer-aware bootloader unlock guidance
               flash download — print download links + fetch latest LineageOS zip
               flash verify   — validate a ROM zip and check device codename match
               flash run      — execute the flash sequence (requires --confirm)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .adb import Adb, AdbCommandError, AdbNotFoundError, AdbDevice
from .apply import apply_plan
from .audit import run_audit
from .bootstrap import recommendations
from .device import collect as collect_device
from .logo import banner
from .camera import CAMERA_PROFILES, find_camera_profile, render_profile, render_profile_list
from .flash import (
    DistroFetchError,
    Fastboot,
    FastbootNotFoundError,
    Heimdall,
    alt_distro_links,
    build_flash_plan,
    detect_manufacturer,
    detect_state,
    developer_options_enabled,
    download_lineage_zip,
    execute_flash_plan,
    heimdall_available,
    is_ab_device,
    lineage_device_url,
    lookup_lineage_build,
    oem_unlock_enabled,
    parse_rom_metadata,
    render_download_options,
    render_flash_plan,
    render_flash_result,
    render_flash_status,
    render_verify_result,
    unlock_guide,
)
from .harden import render_harden_report, run_harden_checks, run_interactive
from .location import render_compat_matrix, render_location_report, run_location_doctor
from .plan import build_plan, render_plan
from .profiles import (
    ProfileError,
    find_profile,
    list_bundled_profiles,
)
from .report import render_json, render_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="los-bootstrap",
        description="CLI-first post-install assistant for LineageOS / degoogled ROMs.",
    )
    parser.add_argument(
        "--serial",
        "-s",
        help="ADB serial of the target device (when more than one is connected).",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the ASCII logo on startup.",
    )
    parser.add_argument(
        "--compact-banner",
        action="store_true",
        help="Use the single-line banner instead of the full logo.",
    )

    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("version", help="Print version and exit.")
    sub.add_parser("devices", help="List ADB-connected devices.")
    sub.add_parser("info", help="Print device, ROM, and build information.")
    sub.add_parser("audit", help="Run the read-only privacy/degoogle audit.")

    p_report = sub.add_parser("report", help="Print device info + audit findings.")
    p_report.add_argument("--json", action="store_true", help="Emit JSON.")

    sub.add_parser("recommend", help="Print non-binding bootstrap recommendations.")

    p_profiles = sub.add_parser("profiles", help="Manage bootstrap profiles.")
    p_profiles_sub = p_profiles.add_subparsers(dest="profiles_command", required=True)
    p_profiles_sub.add_parser("list", help="List bundled profiles.")

    p_plan = sub.add_parser("plan", help="Dry-run a profile against the device.")
    p_plan.add_argument("--profile", required=True, help="Profile name or path.")
    p_plan.add_argument(
        "--profile-dir",
        action="append",
        default=[],
        help="Extra directory to search for profiles (repeatable).",
    )
    p_plan.add_argument(
        "--apk-dir",
        help="Directory containing APKs referenced by sideload steps.",
    )
    p_plan.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip automatic APK downloads; sideload and F-Droid entries will be marked manual.",
    )

    p_apply = sub.add_parser("apply", help="Execute a profile against the device.")
    p_apply.add_argument("--profile", required=True, help="Profile name or path.")
    p_apply.add_argument(
        "--profile-dir",
        action="append",
        default=[],
        help="Extra directory to search for profiles (repeatable).",
    )
    p_apply.add_argument(
        "--apk-dir",
        help="Directory containing APKs referenced by sideload steps, or download cache.",
    )
    p_apply.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip automatic APK downloads; sideload and F-Droid entries will be marked manual.",
    )
    p_apply.add_argument(
        "--confirm",
        action="store_true",
        help="Required to actually run mutating commands.",
    )
    p_apply.add_argument(
        "--dry-run",
        action="store_true",
        help="Print each command without running it.",
    )

    p_harden = sub.add_parser(
        "harden",
        help="Run hardening checks and optionally apply fixes.",
    )
    p_harden.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Walk through each finding interactively, offering to apply fixes.",
    )
    p_harden.add_argument(
        "--root",
        action="store_true",
        help="Include root-only checks (requires adb root / su access).",
    )
    p_harden.add_argument(
        "--confirm",
        action="store_true",
        help="Required to actually apply fix commands in interactive mode.",
    )
    p_harden.add_argument(
        "--dry-run",
        action="store_true",
        help="Print fix commands without executing them (interactive mode only).",
    )

    p_location = sub.add_parser(
        "location",
        help="Location stack diagnostics and app compatibility guidance.",
    )
    p_location_sub = p_location.add_subparsers(dest="location_command", required=True)
    p_location_sub.add_parser(
        "doctor",
        help="Diagnose the location stack on the connected device.",
    )
    p_location_sub.add_parser(
        "compat",
        help="Show the app location compatibility matrix (no device needed).",
    )

    p_camera = sub.add_parser(
        "camera",
        help="GCam port profiles and XML config path guidance (no device needed).",
    )
    p_camera_sub = p_camera.add_subparsers(dest="camera_command", required=True)
    p_camera_sub.add_parser(
        "list-profiles",
        help="List all known device GCam port profiles.",
    )
    p_camera_show = p_camera_sub.add_parser(
        "show",
        help="Show full GCam port profile for a device codename.",
    )
    p_camera_show.add_argument(
        "codename",
        help="Device codename (ro.product.device), e.g. panther, oriole, sunny.",
    )

    p_flash = sub.add_parser(
        "flash",
        help="ROM flashing assistant: bootloader unlock guidance and sideload.",
    )
    p_flash_sub = p_flash.add_subparsers(dest="flash_command", required=True)

    p_flash_sub.add_parser(
        "status",
        help="Detect device state (booted/fastboot/recovery) and manufacturer.",
    )

    p_flash_sub.add_parser(
        "prepare",
        help="Show manufacturer-aware bootloader unlock guide with live pre-checks.",
    )

    p_flash_download = p_flash_sub.add_parser(
        "download",
        help="Print ROM download links and optionally fetch the latest LineageOS zip.",
    )
    p_flash_download.add_argument(
        "codename",
        nargs="?",
        help="Device codename (defaults to the connected device's ro.product.device).",
    )
    p_flash_download.add_argument(
        "--fetch",
        action="store_true",
        help="Download the latest LineageOS zip and verify its SHA-256.",
    )
    p_flash_download.add_argument(
        "--output",
        "-o",
        default=".",
        help="Directory to save the downloaded zip (default: current directory).",
    )
    p_flash_download.add_argument(
        "--no-network",
        action="store_true",
        help="Do not query the LineageOS API; print download page URLs only.",
    )

    p_flash_verify = p_flash_sub.add_parser(
        "verify",
        help="Validate a ROM zip file and check device codename match.",
    )
    p_flash_verify.add_argument(
        "rom",
        help="Path to the LineageOS / AOSP ROM zip file.",
    )

    p_flash_run = p_flash_sub.add_parser(
        "run",
        help="Execute the flash sequence (requires --confirm).",
    )
    p_flash_run.add_argument(
        "rom",
        help="Path to the LineageOS / AOSP ROM zip file.",
    )
    p_flash_run.add_argument(
        "--recovery",
        metavar="IMG",
        help="Path to a recovery image to flash before sideloading (A-only devices).",
    )
    p_flash_run.add_argument(
        "--confirm",
        action="store_true",
        help="Required to run destructive steps (bootloader unlock, flashing).",
    )
    p_flash_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Print each command without executing it.",
    )

    return parser


def _print_banner(args: argparse.Namespace) -> None:
    if args.command is None:
        return  # wizard controls its own screen
    if args.no_banner or args.command == "version":
        return
    sys.stderr.write(banner(compact=args.compact_banner))


def _require_one_device(devices: Sequence[AdbDevice], explicit_serial: Optional[str]) -> str:
    ready = [d for d in devices if d.ready]
    if explicit_serial:
        return explicit_serial
    if not ready:
        raise SystemExit("No ready ADB devices. Plug in a phone and authorize USB debugging.")
    if len(ready) > 1:
        serials = ", ".join(d.serial for d in ready)
        raise SystemExit(
            f"Multiple devices connected ({serials}). Use --serial <id> to pick one."
        )
    return ready[0].serial


def cmd_version() -> int:
    print(f"los-bootstrap {__version__}")
    return 0


def cmd_devices() -> int:
    adb = Adb()
    devices = adb.list_devices()
    if not devices:
        print("(no devices)")
        return 0
    for d in devices:
        marker = " " if d.ready else "!"
        print(f"{marker} {d.serial:24s} {d.state}")
    return 0


def _resolve_target(serial_arg: Optional[str]) -> Adb:
    bootstrap_adb = Adb()
    devices = bootstrap_adb.list_devices()
    serial = _require_one_device(devices, serial_arg)
    return Adb(serial=serial)


def cmd_info(serial: Optional[str]) -> int:
    adb = _resolve_target(serial)
    facts = collect_device(adb)
    print(render_text(facts, report=None), end="")
    return 0


def cmd_audit(serial: Optional[str]) -> int:
    adb = _resolve_target(serial)
    facts = collect_device(adb)
    report = run_audit(adb, facts)
    print(render_text(facts, report), end="")
    return 0 if not report.has_concerns() else 2


def cmd_report(serial: Optional[str], as_json: bool) -> int:
    adb = _resolve_target(serial)
    facts = collect_device(adb)
    report = run_audit(adb, facts)
    if as_json:
        print(render_json(facts, report), end="")
    else:
        print(render_text(facts, report), end="")
    return 0 if not report.has_concerns() else 2


def cmd_recommend(serial: Optional[str]) -> int:
    adb = _resolve_target(serial)
    facts = collect_device(adb)
    report = run_audit(adb, facts)
    for line in recommendations(report):
        print(line)
    return 0


def cmd_profiles_list() -> int:
    profiles = list_bundled_profiles()
    if not profiles:
        print("(no bundled profiles)")
        return 0
    print("Bundled profiles")
    print("----------------")
    for p in profiles:
        first_line = p.description.splitlines()[0] if p.description else ""
        print(f"  {p.name:20s} {first_line}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    profile = find_profile(
        args.profile,
        extra_dirs=[Path(d) for d in args.profile_dir or []],
    )
    adb = _resolve_target(args.serial)
    apk_dir = Path(args.apk_dir) if args.apk_dir else None
    plan = build_plan(adb, profile, apk_dir=apk_dir, fetch=not args.no_fetch)
    print(render_plan(plan), end="")
    return 0


def cmd_harden(args: argparse.Namespace) -> int:
    adb = _resolve_target(args.serial)
    facts = collect_device(adb)
    report = run_harden_checks(adb, facts, root=args.root)

    if args.interactive:
        run_interactive(
            report,
            adb,
            confirm=args.confirm,
            dry_run=args.dry_run,
        )
        return 0

    print(render_harden_report(report), end="")
    return 2 if report.has_failures() else 0


def cmd_camera_list_profiles() -> int:
    print(render_profile_list(), end="")
    return 0


def cmd_camera_show(codename: str) -> int:
    profile = find_camera_profile(codename)
    if profile is None:
        known = ", ".join(p.codename for p in CAMERA_PROFILES)
        sys.stderr.write(
            f"No camera profile found for codename {codename!r}.\n"
            f"Known codenames: {known}\n"
            "\n"
            "GCam ports are matched by SoC, not device name — your device may\n"
            "still work with a port built for the same chip family.\n"
            "\n"
            "  1. Find your SoC: adb shell getprop ro.board.platform\n"
            "  2. Browse celsoazevedo.com for a build matching your SoC.\n"
            "  3. Check your device's XDA thread for the recommended port + XML.\n"
            "  4. If you find a working combo, open a PR to add it to this tool.\n"
        )
        return 2
    print(render_profile(profile), end="")
    return 0


def cmd_location_doctor(args: argparse.Namespace) -> int:
    adb = _resolve_target(args.serial)
    facts = collect_device(adb)
    report = run_location_doctor(adb, facts)
    print(render_location_report(report), end="")
    return 2 if report.has_failures() else 0


def cmd_location_compat() -> int:
    print(render_compat_matrix(), end="")
    return 0


@dataclass
class _FlashContext:
    """Shared device-detection state used by every `flash <subcommand>` path.

    Reading manufacturer / dev_opts / oem_unlock requires the device in
    booted ADB mode; FASTBOOT-specific reads (slot-count, unlocked,
    product) are left to each caller because they vary per command.
    """
    state: "DeviceState"
    manufacturer: "Manufacturer"
    codename: str
    dev_opts: Optional[bool]
    oem_unlock: Optional[bool]
    target_adb: Optional[Adb]
    fb: Fastboot


def _detect_flash_context(serial: Optional[str]) -> "_FlashContext":
    from .flash.models import DeviceState, Manufacturer

    adb = Adb()
    adb_out = adb.raw("devices").stdout
    fb = Fastboot()
    try:
        fb_out = fb._run([fb.binary, "devices"]).stdout
    except Exception:
        fb_out = ""

    state = detect_state(adb_out, fb_out)
    manufacturer = Manufacturer.GENERIC
    codename = ""
    dev_opts: Optional[bool] = None
    oem_unlock: Optional[bool] = None
    target_adb: Optional[Adb] = None

    if state == DeviceState.BOOTED:
        try:
            target_adb = _resolve_target(serial)
            codename = target_adb.getprop("ro.product.device")
            raw_mfr = target_adb.getprop("ro.product.manufacturer")
            manufacturer = detect_manufacturer(raw_mfr)
            dev_opts = developer_options_enabled(target_adb)
            oem_unlock = oem_unlock_enabled(target_adb)
        except Exception:
            pass

    return _FlashContext(
        state=state,
        manufacturer=manufacturer,
        codename=codename,
        dev_opts=dev_opts,
        oem_unlock=oem_unlock,
        target_adb=target_adb,
        fb=fb,
    )


def cmd_flash_status(serial: Optional[str]) -> int:
    from .flash.models import DeviceState

    ctx = _detect_flash_context(serial)
    bl_unlocked: Optional[bool] = None
    codename = ctx.codename
    manufacturer = ctx.manufacturer if ctx.state == DeviceState.BOOTED else None

    if ctx.state == DeviceState.FASTBOOT:
        try:
            unlocked = ctx.fb.getvar("unlocked")
            bl_unlocked = unlocked.lower() == "yes"
            codename = ctx.fb.getvar("product")
        except Exception:
            pass

    print(
        render_flash_status(
            ctx.state, manufacturer, codename, bl_unlocked, ctx.dev_opts, ctx.oem_unlock
        ),
        end="",
    )
    return 0


def cmd_flash_prepare(serial: Optional[str]) -> int:
    from .flash.models import DeviceState, Manufacturer

    ctx = _detect_flash_context(serial)

    if ctx.codename or ctx.state != DeviceState.UNKNOWN:
        print(
            render_flash_status(
                ctx.state, ctx.manufacturer, ctx.codename, None, ctx.dev_opts, ctx.oem_unlock
            ),
            end="",
        )

    print(unlock_guide(ctx.manufacturer))

    if ctx.manufacturer == Manufacturer.SAMSUNG and not heimdall_available():
        from .flash.guide import samsung_odin_guide as _odin
        print("─── Heimdall not found on PATH — Odin fallback ───\n")
        print(_odin())

    return 0


def cmd_flash_download(args: argparse.Namespace) -> int:
    codename = (args.codename or "").strip()
    if not codename:
        try:
            target_adb = _resolve_target(args.serial)
            codename = target_adb.getprop("ro.product.device").strip()
        except SystemExit:
            sys.stderr.write(
                "error: no codename given and no device connected.\n"
                "Pass a codename: `los-bootstrap flash download <codename>`.\n"
            )
            return 2
        except Exception:
            codename = ""

    if not codename:
        sys.stderr.write("error: could not determine device codename.\n")
        return 2

    page_url = lineage_device_url(codename)
    alt = alt_distro_links(codename)

    build = None
    api_error: Optional[str] = None
    if not args.no_network:
        try:
            build = lookup_lineage_build(codename)
        except DistroFetchError as exc:
            api_error = str(exc)

    downloaded_path = None
    if args.fetch:
        if build is None:
            sys.stderr.write(
                "error: cannot --fetch without a LineageOS build for this codename.\n"
            )
            if api_error:
                sys.stderr.write(f"  reason: {api_error}\n")
            return 2
        out_dir = Path(args.output)
        try:
            downloaded_path = download_lineage_zip(
                build,
                out_dir,
                progress=_print_download_progress,
            )
            sys.stderr.write("\n")
        except DistroFetchError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 1

    print(
        render_download_options(
            codename=codename,
            build=build,
            page_url=page_url,
            alt_links=alt,
            api_error=api_error,
            downloaded_path=downloaded_path,
            network_skipped=args.no_network,
        ),
        end="",
    )
    return 0


def _print_download_progress(read: int, total: int) -> None:
    if total <= 0:
        sys.stderr.write(f"\rdownloaded {read // (1024 * 1024)} MiB")
    else:
        pct = (read * 100) // total
        sys.stderr.write(
            f"\rdownloading… {read // (1024 * 1024)}/{total // (1024 * 1024)} MiB "
            f"({pct}%)"
        )
    sys.stderr.flush()


def cmd_flash_verify(rom: str, serial: Optional[str]) -> int:
    import zipfile

    zip_path = Path(rom)
    if not zip_path.exists():
        sys.stderr.write(f"error: ROM file not found: {zip_path}\n")
        return 2

    valid = False
    try:
        with zipfile.ZipFile(zip_path):
            valid = True
    except zipfile.BadZipFile:
        pass

    metadata = parse_rom_metadata(zip_path) if valid else None

    codename = ""
    if valid:
        try:
            target_adb = _resolve_target(serial)
            codename = target_adb.getprop("ro.product.device")
        except Exception:
            pass

    print(render_verify_result(zip_path, valid, metadata, codename), end="")
    return 0 if valid else 2


def cmd_flash_run(args: argparse.Namespace) -> int:
    from .flash.models import DeviceState, Manufacturer

    rom_path = Path(args.rom)
    if not rom_path.exists():
        sys.stderr.write(f"error: ROM file not found: {rom_path}\n")
        return 2

    recovery_path = Path(args.recovery) if args.recovery else None
    if recovery_path and not recovery_path.exists():
        sys.stderr.write(f"error: recovery image not found: {recovery_path}\n")
        return 2

    ctx = _detect_flash_context(args.serial)
    ab = False
    if ctx.state in (DeviceState.FASTBOOT, DeviceState.BOOTED):
        try:
            ab = is_ab_device(ctx.fb.getvar("slot-count"))
        except Exception:
            pass

    hl = Heimdall() if ctx.manufacturer == Manufacturer.SAMSUNG else None
    hl_avail = heimdall_available() if ctx.manufacturer == Manufacturer.SAMSUNG else False

    plan = build_flash_plan(
        manufacturer=ctx.manufacturer,
        device_codename=ctx.codename,
        rom_path=rom_path,
        recovery_path=recovery_path,
        ab_device=ab,
        heimdall_available=hl_avail,
    )

    if not args.confirm and not args.dry_run:
        print(render_flash_plan(plan), end="")
        sys.stderr.write(
            "Refusing to flash without --confirm. "
            "Re-run with `flash run <rom> --confirm` to execute, "
            "or add --dry-run to preview.\n"
        )
        return 2

    target_adb = ctx.target_adb if ctx.target_adb is not None else Adb()

    result = execute_flash_plan(
        plan,
        adb=target_adb,
        fastboot=ctx.fb,
        heimdall=hl,
        confirm=args.confirm,
        dry_run=args.dry_run,
    )
    print(render_flash_result(result), end="")
    return 1 if result.had_errors() else 0


def cmd_apply(args: argparse.Namespace) -> int:
    profile = find_profile(
        args.profile,
        extra_dirs=[Path(d) for d in args.profile_dir or []],
    )
    adb = _resolve_target(args.serial)
    apk_dir = Path(args.apk_dir) if args.apk_dir else None
    plan = build_plan(adb, profile, apk_dir=apk_dir, fetch=not args.no_fetch)

    if not args.confirm and not args.dry_run:
        sys.stderr.write(render_plan(plan))
        sys.stderr.write(
            "\nrefusing to apply without --confirm. "
            "Re-run with `apply --profile ... --confirm` to execute, "
            "or add --dry-run to preview.\n"
        )
        return 2

    result = apply_plan(adb, plan, dry_run=args.dry_run, apk_dir=apk_dir)
    return 1 if result.had_errors() else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _print_banner(args)

    try:
        if args.command is None:
            from .wizard import run_wizard
            return run_wizard(getattr(args, "serial", None))

        if args.command == "version":
            return cmd_version()
        if args.command == "devices":
            return cmd_devices()
        if args.command == "info":
            return cmd_info(args.serial)
        if args.command == "audit":
            return cmd_audit(args.serial)
        if args.command == "report":
            return cmd_report(args.serial, args.json)
        if args.command == "recommend":
            return cmd_recommend(args.serial)
        if args.command == "profiles":
            if args.profiles_command == "list":
                return cmd_profiles_list()
        if args.command == "plan":
            return cmd_plan(args)
        if args.command == "apply":
            return cmd_apply(args)
        if args.command == "harden":
            return cmd_harden(args)
        if args.command == "location":
            if args.location_command == "doctor":
                return cmd_location_doctor(args)
            if args.location_command == "compat":
                return cmd_location_compat()
        if args.command == "camera":
            if args.camera_command == "list-profiles":
                return cmd_camera_list_profiles()
            if args.camera_command == "show":
                return cmd_camera_show(args.codename)
        if args.command == "flash":
            if args.flash_command == "status":
                return cmd_flash_status(args.serial)
            if args.flash_command == "prepare":
                return cmd_flash_prepare(args.serial)
            if args.flash_command == "download":
                return cmd_flash_download(args)
            if args.flash_command == "verify":
                return cmd_flash_verify(args.rom, args.serial)
            if args.flash_command == "run":
                return cmd_flash_run(args)
    except AdbNotFoundError as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.stderr.write("Install Android platform-tools so `adb` is on PATH.\n")
        return 127
    except FastbootNotFoundError as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.stderr.write("Install Android platform-tools so `fastboot` is on PATH.\n")
        return 127
    except AdbCommandError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    except ProfileError as exc:
        sys.stderr.write(f"profile error: {exc}\n")
        return 2

    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable; keeps mypy/type-checkers happy


if __name__ == "__main__":
    raise SystemExit(main())
