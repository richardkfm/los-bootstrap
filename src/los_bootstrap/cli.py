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

Phase 11 commands (flash lifecycle):
    flash update   — check whether the installed LineageOS build is current (read-only)
    flash check    — post-flash first-boot verification (read-only)
    flash backup   — pre-flash backup guidance (no device required)
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
    LineageBuild,
    alt_distro_links,
    backup_guide,
    build_flash_plan,
    detect_manufacturer,
    detect_state,
    developer_options_enabled,
    download_lineage_zip,
    evaluate_rom_update,
    execute_flash_plan,
    heimdall_available,
    is_ab_device,
    lineage_device_url,
    lookup_lineage_build,
    lookup_lineage_builds,
    oem_unlock_enabled,
    parse_rom_metadata,
    pick_update_candidates,
    render_download_options,
    render_flash_plan,
    render_flash_result,
    render_flash_status,
    render_first_boot_report,
    render_update_report,
    render_verify_result,
    run_first_boot,
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


# Exit codes. 2 is also what argparse uses for usage errors.
EXIT_OK = 0
EXIT_ERROR = 1      # runtime failure (adb/fastboot/network)
EXIT_USAGE = 2      # bad invocation, missing file, unknown profile
EXIT_FINDINGS = 3   # checks ran fine but issues need attention

_EPILOG = """\
examples:
  los-bootstrap                                  launch the interactive wizard
  los-bootstrap report --json                    device info + audit as JSON
  los-bootstrap plan --profile privacy-default   preview a bootstrap profile
  los-bootstrap harden --interactive --confirm   walk through hardening fixes
  los-bootstrap flash download panther --fetch   fetch the latest LineageOS zip

exit codes:
  0 success   1 runtime error   2 usage/profile error   3 checks found issues
"""


def _add_common_options(parser: argparse.ArgumentParser, *, suppress: bool = False) -> None:
    """Add the global options to a parser.

    On subparsers, defaults are SUPPRESS so `los-bootstrap audit -s X`
    works without a late default clobbering a value parsed by the main
    parser (`los-bootstrap -s X audit`).
    """
    kw_str = {"default": argparse.SUPPRESS} if suppress else {}
    kw_flag = {"default": argparse.SUPPRESS} if suppress else {}
    parser.add_argument(
        "--serial",
        "-s",
        help="ADB serial of the target device (when more than one is connected).",
        **kw_str,
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Suppress the ASCII logo on startup.",
        **kw_flag,
    )
    parser.add_argument(
        "--compact-banner",
        action="store_true",
        help="Use the single-line banner instead of the full logo.",
        **kw_flag,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="los-bootstrap",
        description="CLI-first post-install assistant for LineageOS / degoogled ROMs.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_options(parser)
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"los-bootstrap {__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=False)

    leaves: list[argparse.ArgumentParser] = []

    leaves.append(sub.add_parser("version", help="Print version and exit."))
    leaves.append(sub.add_parser("devices", help="List ADB-connected devices."))
    leaves.append(sub.add_parser("info", help="Print device, ROM, and build information."))
    leaves.append(sub.add_parser("audit", help="Run the read-only privacy/degoogle audit."))

    p_report = sub.add_parser("report", help="Print device info + audit findings.")
    p_report.add_argument("--json", action="store_true", help="Emit JSON.")
    leaves.append(p_report)

    leaves.append(
        sub.add_parser("recommend", help="Print non-binding bootstrap recommendations.")
    )

    p_profiles = sub.add_parser("profiles", help="Manage bootstrap profiles.")
    p_profiles_sub = p_profiles.add_subparsers(dest="profiles_command", required=True)
    leaves.append(p_profiles_sub.add_parser("list", help="List bundled profiles."))

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
    leaves.append(p_plan)

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
    leaves.append(p_apply)

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
    leaves.append(p_harden)

    p_location = sub.add_parser(
        "location",
        help="Location stack diagnostics and app compatibility guidance.",
    )
    p_location_sub = p_location.add_subparsers(dest="location_command", required=True)
    leaves.append(p_location_sub.add_parser(
        "doctor",
        help="Diagnose the location stack on the connected device.",
    ))
    leaves.append(p_location_sub.add_parser(
        "compat",
        help="Show the app location compatibility matrix (no device needed).",
    ))

    p_camera = sub.add_parser(
        "camera",
        help="GCam port profiles and XML config path guidance (no device needed).",
    )
    p_camera_sub = p_camera.add_subparsers(dest="camera_command", required=True)
    leaves.append(p_camera_sub.add_parser(
        "list-profiles",
        help="List all known device GCam port profiles.",
    ))
    p_camera_show = p_camera_sub.add_parser(
        "show",
        help="Show full GCam port profile for a device codename.",
    )
    p_camera_show.add_argument(
        "codename",
        help="Device codename (ro.product.device), e.g. panther, oriole, sunny.",
    )
    leaves.append(p_camera_show)

    p_flash = sub.add_parser(
        "flash",
        help="ROM flashing assistant: bootloader unlock guidance and sideload.",
    )
    p_flash_sub = p_flash.add_subparsers(dest="flash_command", required=True)

    leaves.append(p_flash_sub.add_parser(
        "status",
        help="Detect device state (booted/fastboot/recovery) and manufacturer.",
    ))

    leaves.append(p_flash_sub.add_parser(
        "prepare",
        help="Show manufacturer-aware bootloader unlock guide with live pre-checks.",
    ))

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
    leaves.append(p_flash_download)

    p_flash_verify = p_flash_sub.add_parser(
        "verify",
        help="Validate a ROM zip file and check device codename match.",
    )
    p_flash_verify.add_argument(
        "rom",
        help="Path to the LineageOS / AOSP ROM zip file.",
    )
    leaves.append(p_flash_verify)

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
    leaves.append(p_flash_run)

    p_flash_update = p_flash_sub.add_parser(
        "update",
        help="Check whether the installed LineageOS build is up to date (read-only).",
    )
    p_flash_update.add_argument(
        "--no-network",
        action="store_true",
        help="Skip the LineageOS API lookup; report the ROM as unverifiable.",
    )
    leaves.append(p_flash_update)

    leaves.append(p_flash_sub.add_parser(
        "check",
        help="Post-flash first-boot verification of a freshly flashed device (read-only).",
    ))

    leaves.append(p_flash_sub.add_parser(
        "backup",
        help="Print pre-flash backup guidance (no device required).",
    ))

    for leaf in leaves:
        _add_common_options(leaf, suppress=True)

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
        by_serial = {d.serial: d for d in devices}
        dev = by_serial.get(explicit_serial)
        if dev is None:
            known = ", ".join(sorted(by_serial)) or "(none)"
            raise SystemExit(
                f"No device with serial {explicit_serial!r}. Connected: {known}."
            )
        if not dev.ready:
            raise SystemExit(
                f"Device {explicit_serial!r} is {dev.state!r}; "
                "authorize USB debugging on the device and retry."
            )
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
    return EXIT_OK if not report.has_concerns() else EXIT_FINDINGS


def cmd_report(serial: Optional[str], as_json: bool) -> int:
    adb = _resolve_target(serial)
    facts = collect_device(adb)
    report = run_audit(adb, facts)
    if as_json:
        print(render_json(facts, report), end="")
    else:
        print(render_text(facts, report), end="")
    return EXIT_OK if not report.has_concerns() else EXIT_FINDINGS


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
    return EXIT_FINDINGS if report.has_failures() else EXIT_OK


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
    return EXIT_FINDINGS if report.has_failures() else EXIT_OK


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
        fb_out = fb.raw("devices").stdout
    except Exception:
        fb_out = ""

    state = detect_state(adb_out, fb_out)
    if state == DeviceState.UNKNOWN and heimdall_available():
        try:
            if Heimdall().detect():
                state = DeviceState.DOWNLOAD
        except Exception:
            pass
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
    if args.fetch and args.no_network:
        sys.stderr.write("error: --fetch and --no-network are mutually exclusive.\n")
        return 2

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
    mismatch = bool(
        metadata and codename and metadata.pre_device.lower() != codename.lower()
    )
    return EXIT_FINDINGS if (not valid or mismatch) else EXIT_OK


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

    metadata = parse_rom_metadata(rom_path)
    if (
        metadata
        and ctx.codename
        and metadata.pre_device.lower() != ctx.codename.lower()
    ):
        sys.stderr.write(
            f"error: ROM targets {metadata.pre_device!r} but the connected "
            f"device is {ctx.codename!r}.\n"
            "Flashing a ROM built for a different device can brick it. "
            "Run `los-bootstrap flash verify <rom.zip>` for details.\n"
        )
        return 2

    # `fastboot getvar` blocks until a fastboot device appears, so only ask
    # fastboot when the device is actually in fastboot mode; when booted,
    # read the slot suffix over ADB instead.
    ab = False
    if ctx.state == DeviceState.FASTBOOT:
        try:
            ab = is_ab_device(ctx.fb.getvar("slot-count"))
        except Exception:
            pass
    elif ctx.state == DeviceState.BOOTED and ctx.target_adb is not None:
        try:
            ab = bool(ctx.target_adb.getprop("ro.boot.slot_suffix"))
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


def cmd_flash_update(args: argparse.Namespace) -> int:
    from .flash.models import DeviceState, RomUpdateState

    ctx = _detect_flash_context(args.serial)
    if ctx.state != DeviceState.BOOTED or ctx.target_adb is None:
        sys.stderr.write(
            "error: `flash update` needs a booted ADB device "
            "(none detected — is USB debugging enabled?).\n"
        )
        return EXIT_USAGE

    facts = collect_device(ctx.target_adb)
    codename = (facts.codename or "").strip()

    if not args.no_network and not codename:
        sys.stderr.write(
            "error: could not determine device codename (ro.product.device is empty); "
            "cannot look up official builds.\n"
        )
        return EXIT_USAGE

    latest: Optional[LineageBuild] = None
    latest_overall: Optional[LineageBuild] = None
    api_error: Optional[str] = None
    lookup_performed = not args.no_network

    if lookup_performed:
        try:
            builds = lookup_lineage_builds(codename)
        except DistroFetchError as exc:
            # Mirror `flash download`: an unreachable API degrades to a
            # rendered report plus a page link, not a bare error.
            api_error = str(exc)
            lookup_performed = False
        else:
            latest, latest_overall = pick_update_candidates(
                facts.lineage_version, builds
            )

    result = evaluate_rom_update(
        facts,
        latest,
        latest_overall,
        lookup_performed=lookup_performed,
        note=(
            "network lookup skipped (--no-network)"
            if args.no_network
            else ("the LineageOS API could not be reached" if api_error else None)
        ),
    )

    print(
        render_update_report(
            facts,
            result,
            latest,
            api_error=api_error,
            page_url=lineage_device_url(codename) if codename else None,
        ),
        end="",
    )
    return EXIT_FINDINGS if result.state is RomUpdateState.OUTDATED else EXIT_OK


def cmd_flash_check(args: argparse.Namespace) -> int:
    from .flash.models import DeviceState

    ctx = _detect_flash_context(args.serial)
    if ctx.state != DeviceState.BOOTED or ctx.target_adb is None:
        sys.stderr.write(
            "error: `flash check` needs a booted ADB device "
            "(none detected — is USB debugging enabled?).\n"
        )
        return EXIT_USAGE

    facts = collect_device(ctx.target_adb)
    report = run_first_boot(ctx.target_adb, facts)
    print(render_first_boot_report(report), end="")
    return EXIT_FINDINGS if report.has_failures() else EXIT_OK


def cmd_flash_backup() -> int:
    print(backup_guide(), end="")
    return EXIT_OK


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
            if args.flash_command == "update":
                return cmd_flash_update(args)
            if args.flash_command == "check":
                return cmd_flash_check(args)
            if args.flash_command == "backup":
                return cmd_flash_backup()
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
