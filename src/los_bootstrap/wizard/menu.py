"""Interactive wizard screens and routing.

Entry point: run_wizard(serial) -> int

Each _screen_* function takes a WizardContext and returns a routing token
string. The main loop dispatches on that token. This keeps screens unit-
testable: patch ask_select to return known tokens without a TTY.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .. import __version__
from ..logo import banner
from .prompt import BOLD, CYAN, GREEN, RED, RESET, YELLOW, ask_confirm, ask_select, ask_text, clear_screen
from .render import render_finding_detail


# ── Context ───────────────────────────────────────────────────────────────────

@dataclass
class WizardContext:
    serial: Optional[str] = None
    offline: bool = False
    _adb: object = field(default=None, repr=False)
    _facts: object = field(default=None, repr=False)
    _audit_report: object = field(default=None, repr=False)
    _harden_report: object = field(default=None, repr=False)

    def get_adb(self):
        if self._adb is None:
            from ..adb import Adb
            self._adb = Adb(serial=self.serial)
        return self._adb

    def get_facts(self):
        if self._facts is None:
            from ..device import collect
            self._facts = collect(self.get_adb())
        return self._facts

    def get_audit(self):
        if self._audit_report is None:
            from ..audit import run_audit
            self._audit_report = run_audit(self.get_adb(), self.get_facts())
        return self._audit_report

    def get_harden(self, root: bool = False):
        if self._harden_report is None:
            from ..harden import run_harden_checks
            self._harden_report = run_harden_checks(self.get_adb(), self.get_facts(), root=root)
        return self._harden_report


# ── Helpers ───────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{title}{RESET}")
    print("─" * min(len(title), 60))


def _device_line(ctx: WizardContext) -> str:
    if ctx.offline:
        return f"{YELLOW}  ⚠  No ADB device — offline mode (camera & location compat only){RESET}"
    try:
        facts = ctx.get_facts()
        rom = f"LineageOS {facts.lineage_version}" if facts.is_lineage else "AOSP-derived"
        return f"{GREEN}  ✓  {facts.manufacturer} {facts.model}  ({facts.codename} / {rom} / Android {facts.android_release}){RESET}"
    except Exception as exc:
        return f"{RED}  ✗  Device error: {exc}{RESET}"


def _require_device(ctx: WizardContext) -> bool:
    if ctx.offline:
        print(f"\n{RED}  This option requires an ADB-connected device.{RESET}")
        print("  Connect a device with USB debugging enabled and restart the wizard.")
        input("\n  Press Enter to continue...")
        return False
    return True


# ── Splash / device detection ─────────────────────────────────────────────────

def _screen_splash(ctx: WizardContext) -> None:
    clear_screen()
    sys.stderr.write(banner(compact=False))
    sys.stderr.flush()
    print("  Scanning for ADB devices...")
    print(_device_line(ctx))
    input("\n  Press Enter to continue...")


# ── Main menu ─────────────────────────────────────────────────────────────────

def _screen_main_menu(ctx: WizardContext) -> str:
    clear_screen()
    _header("Main menu")
    print(_device_line(ctx))
    print()

    choices = [
        "Audit — check privacy and degoogle status  [read-only]",
        "Harden — review and fix security settings  [can apply changes]",
        "Bootstrap — install apps and apply settings  [can apply changes]",
        "Location — diagnose location stack",
        "Camera — GCam port profiles  [no ADB needed]",
        "Flash — bootloader unlock + ROM flashing  [advanced]",
        "Exit",
    ]
    choice = ask_select("What would you like to do?", choices)
    if choice is None or "Exit" in choice:
        return "exit"
    if "Audit" in choice:
        return "audit"
    if "Harden" in choice:
        return "harden"
    if "Bootstrap" in choice:
        return "bootstrap"
    if "Location" in choice:
        return "location"
    if "Camera" in choice:
        return "camera"
    if "Flash" in choice:
        return "flash"
    return "exit"


# ── Audit ─────────────────────────────────────────────────────────────────────

def _screen_audit(ctx: WizardContext) -> str:
    if not _require_device(ctx):
        return "main"
    clear_screen()
    _header("Audit — privacy and degoogle status")
    print("  Running audit...", end="", flush=True)
    try:
        report = ctx.get_audit()
    except Exception as exc:
        print(f"\n{RED}  Error: {exc}{RESET}")
        input("\n  Press Enter to go back...")
        return "main"
    print(" done.\n")

    from ..report import render_text
    print(render_text(ctx.get_facts(), report))

    actionable = [f for f in report.findings
                  if f.severity.value in ("warn", "high")]

    choices = []
    if actionable:
        choices.append("Read a full explanation of a specific finding")
    choices += [
        "Go to Harden for more security checks",
        "Back to main menu",
    ]
    choice = ask_select("What next?", choices)
    if choice is None or "Back" in choice or "main" in choice:
        return "main"
    if "explanation" in choice:
        return _screen_audit_finding_detail(ctx, actionable)
    if "Harden" in choice:
        return "harden"
    return "main"


def _screen_audit_finding_detail(ctx: WizardContext, actionable: list) -> str:
    titles = [f"{f.severity.value.upper()}  {f.title}" for f in actionable]
    titles.append("← Back to audit results")
    choice = ask_select("Which finding?", titles)
    if choice is None or "Back" in choice:
        return _screen_audit(ctx)

    idx = titles.index(choice)
    if idx < len(actionable):
        f = actionable[idx]
        clear_screen()
        _header(f.title)
        print(render_finding_detail(f.check, f.title))
        input("\n  Press Enter to go back...")
    return _screen_audit(ctx)


# ── Harden ────────────────────────────────────────────────────────────────────

def _screen_harden(ctx: WizardContext) -> str:
    if not _require_device(ctx):
        return "main"
    clear_screen()
    _header("Harden — security checks")

    choices = [
        "Run checks (read-only)",
        "Run checks + walk through fixes interactively",
        "Run checks including root-only checks",
        "Back to main menu",
    ]
    choice = ask_select("Harden options:", choices)
    if choice is None or "Back" in choice:
        return "main"

    root = "root" in choice
    interactive = "interactively" in choice

    print("\n  Running hardening checks...", end="", flush=True)
    try:
        ctx._harden_report = None  # reset so root flag takes effect
        report = ctx.get_harden(root=root)
    except Exception as exc:
        print(f"\n{RED}  Error: {exc}{RESET}")
        input("\n  Press Enter to go back...")
        return "main"
    print(" done.\n")

    if interactive:
        return _screen_harden_interactive(ctx, report)

    from ..harden import render_harden_report
    print(render_harden_report(report))
    input("\n  Press Enter to go back...")
    return "main"


def _screen_harden_interactive(ctx: WizardContext, report) -> str:
    from ..harden.models import HardenStatus
    from ..harden.interactive import run_interactive

    actionable = [f for f in report.findings
                  if f.status in (HardenStatus.WARN, HardenStatus.FAIL)]
    if not actionable:
        print(f"\n{GREEN}  All checks passed — nothing to fix.{RESET}")
        input("\n  Press Enter to go back...")
        return "main"

    clear_screen()
    _header("Interactive harden")
    print(f"  {len(actionable)} {'issue' if len(actionable) == 1 else 'issues'} found.\n")

    confirmed = ask_confirm(
        "  Apply fixes? (you will be prompted per finding)", default=False
    )
    if not confirmed:
        print("\n  Aborted — no changes made.")
        input("\n  Press Enter to go back...")
        return "main"

    run_interactive(report, ctx.get_adb(), confirm=True, dry_run=False)
    input("\n  Press Enter to go back...")
    return "main"


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def _screen_bootstrap(ctx: WizardContext) -> str:
    if not _require_device(ctx):
        return "main"
    clear_screen()
    _header("Bootstrap — install apps and apply settings")

    from ..profiles import list_bundled_profiles
    profiles = list_bundled_profiles()
    profile_choices = [f"{p.name:<20} {p.description.splitlines()[0] if p.description else ''}"
                       for p in profiles]
    profile_choices += ["Enter a path to a custom profile", "Back to main menu"]

    choice = ask_select("Choose a bootstrap profile:", profile_choices)
    if choice is None or "Back" in choice:
        return "main"

    if "custom profile" in choice:
        path_str = ask_text("  Profile path")
        if not path_str:
            return "bootstrap"
        profile_name = path_str
    else:
        idx = profile_choices.index(choice)
        profile_name = profiles[idx].name

    return _screen_bootstrap_plan(ctx, profile_name)


def _screen_bootstrap_plan(ctx: WizardContext, profile_name: str) -> str:
    clear_screen()
    _header(f"Plan: {profile_name}")

    from ..profiles import find_profile, ProfileError
    from ..plan import build_plan, render_plan

    print("  Building plan (fetching APKs where declared)…", flush=True)
    try:
        profile = find_profile(profile_name)
        plan = build_plan(ctx.get_adb(), profile, fetch=True)
    except ProfileError as exc:
        print(f"\n{RED}  Profile error: {exc}{RESET}")
        input("\n  Press Enter to go back...")
        return "bootstrap"
    except Exception as exc:
        print(f"\n{RED}  Error building plan: {exc}{RESET}")
        input("\n  Press Enter to go back...")
        return "bootstrap"

    print(render_plan(plan))

    choices = [
        "Apply this plan",
        "Back to profile picker",
        "Back to main menu",
    ]
    choice = ask_select("What next?", choices)
    if choice is None or "main menu" in choice:
        return "main"
    if "profile picker" in choice:
        return "bootstrap"
    if "Apply" in choice:
        return _screen_bootstrap_apply(ctx, plan)
    return "main"


def _screen_bootstrap_apply(ctx: WizardContext, plan) -> str:
    print(f"\n{YELLOW}  This will execute mutating ADB commands on the device.{RESET}")
    confirmed = ask_confirm("  Proceed?", default=False)
    if not confirmed:
        print("  Aborted.")
        input("\n  Press Enter to go back...")
        return "main"

    from ..apply import apply_plan
    result = apply_plan(ctx.get_adb(), plan, dry_run=False)
    counts = result.counts()
    print(f"\n  Done — ok: {counts.get('ok', 0)}, "
          f"manual: {counts.get('manual', 0)}, "
          f"skipped: {counts.get('skipped', 0)}, "
          f"errors: {counts.get('error', 0)}")
    input("\n  Press Enter to go back...")
    return "main"


# ── Location ──────────────────────────────────────────────────────────────────

def _screen_location(ctx: WizardContext) -> str:
    clear_screen()
    _header("Location tools")

    choices = [
        "Diagnose location stack on this device  [ADB required]",
        "App compatibility matrix  [no device needed]",
        "Back to main menu",
    ]
    choice = ask_select("Location options:", choices)
    if choice is None or "Back" in choice:
        return "main"

    if "Diagnose" in choice:
        if not _require_device(ctx):
            return "location"
        print("\n  Running location doctor...", end="", flush=True)
        try:
            from ..location import run_location_doctor, render_location_report
            report = run_location_doctor(ctx.get_adb(), ctx.get_facts())
        except Exception as exc:
            print(f"\n{RED}  Error: {exc}{RESET}")
            input("\n  Press Enter to go back...")
            return "main"
        print(" done.\n")
        print(render_location_report(report))
        input("\n  Press Enter to go back...")
        return "main"

    if "compatibility" in choice:
        from ..location import render_compat_matrix
        clear_screen()
        _header("App location compatibility matrix")
        print(render_compat_matrix())
        input("\n  Press Enter to go back...")
        return "main"

    return "main"


# ── Camera ────────────────────────────────────────────────────────────────────

def _screen_camera(ctx: WizardContext) -> str:
    clear_screen()
    _header("Camera — GCam port profiles")

    choices = [
        "List all known device profiles",
        "Look up a specific device by codename",
        "Back to main menu",
    ]
    choice = ask_select("Camera options:", choices)
    if choice is None or "Back" in choice:
        return "main"

    if "List" in choice:
        from ..camera import render_profile_list
        clear_screen()
        _header("GCam port profiles")
        print(render_profile_list())
        input("\n  Press Enter to go back...")
        return "camera"

    if "Look up" in choice:
        codename = ask_text("  Device codename (e.g. panther, oriole, sunny)")
        if codename:
            from ..camera import find_camera_profile, render_profile, CAMERA_PROFILES
            profile = find_camera_profile(codename)
            clear_screen()
            if profile:
                _header(f"Profile: {codename}")
                print(render_profile(profile))
            else:
                known = ", ".join(p.codename for p in CAMERA_PROFILES)
                print(f"\n{RED}  No profile found for {codename!r}.{RESET}")
                print(f"  Known codenames: {known}")
                print("\n  Your device may still work with a port built for the same SoC.")
                print("  Check celsoazevedo.com and your device's XDA thread.")
            input("\n  Press Enter to go back...")
        return "camera"

    return "main"


# ── Flash ─────────────────────────────────────────────────────────────────────

def _screen_flash(ctx: WizardContext) -> str:
    clear_screen()
    _header("Flash — bootloader unlock + ROM flashing")
    print(f"  {YELLOW}⚠  Flashing can brick your device. Read each screen carefully.{RESET}\n")

    print("  Detecting device flash state…", end="", flush=True)
    try:
        from ..cli import _detect_flash_context
        from ..flash import DeviceState, render_flash_status
        fctx = _detect_flash_context(ctx.serial)
    except Exception as exc:
        print(f"\n{RED}  Error: {exc}{RESET}")
        input("\n  Press Enter to go back...")
        return "main"
    print(" done.\n")

    bl_unlocked = None
    if fctx.state == DeviceState.FASTBOOT:
        try:
            unlocked = fctx.fb.getvar("unlocked")
            bl_unlocked = unlocked.lower() == "yes"
        except Exception:
            pass

    print(render_flash_status(
        fctx.state, fctx.manufacturer, fctx.codename, bl_unlocked, fctx.dev_opts, fctx.oem_unlock
    ))

    choices = [
        "Show bootloader unlock guidance for this device  [read-only]",
        "Download a ROM (LineageOS or alt distros)",
        "Verify a ROM zip",
        "Flash a ROM  [destructive — needs confirmation]",
        "Back to main menu",
    ]
    choice = ask_select("Flash options:", choices)
    if choice is None or "Back" in choice:
        return "main"
    if "unlock guidance" in choice:
        return _screen_flash_prepare(ctx, fctx)
    if "Download" in choice:
        return _screen_flash_download(ctx, fctx)
    if "Verify" in choice:
        return _screen_flash_verify(ctx)
    if "Flash a ROM" in choice:
        return _screen_flash_run(ctx, fctx)
    return "flash"


def _screen_flash_prepare(ctx: WizardContext, fctx) -> str:
    from ..flash import Manufacturer, heimdall_available, samsung_odin_guide, unlock_guide

    clear_screen()
    _header("Bootloader unlock guidance")
    print(unlock_guide(fctx.manufacturer))

    if fctx.manufacturer == Manufacturer.SAMSUNG and not heimdall_available():
        print("─── Heimdall not found on PATH — Odin fallback ───\n")
        print(samsung_odin_guide())

    input("\n  Press Enter to go back...")
    return "flash"


def _screen_flash_download(ctx: WizardContext, fctx) -> str:
    import sys
    from ..flash import (
        DistroFetchError,
        alt_distro_links,
        download_lineage_zip,
        lineage_device_url,
        lookup_lineage_build,
        render_download_options,
    )

    clear_screen()
    _header("Download a ROM")

    default_codename = fctx.codename or ""
    if not default_codename and not ctx.offline:
        try:
            default_codename = ctx.get_facts().codename or ""
        except Exception:
            pass
    prompt = "  Device codename"
    if default_codename:
        prompt += f" [{default_codename}]"
    codename = ask_text(prompt) or default_codename
    codename = codename.strip()
    if not codename:
        print(f"\n{RED}  No codename given.{RESET}")
        input("\n  Press Enter to go back...")
        return "flash"

    print("\n  Querying LineageOS API for the latest build…", flush=True)
    page_url = lineage_device_url(codename)
    alt = alt_distro_links(codename)
    build = None
    api_error = None
    try:
        build = lookup_lineage_build(codename)
    except DistroFetchError as exc:
        api_error = str(exc)

    downloaded_path = None
    if build is not None:
        size_mib = build.size // (1024 * 1024) if build.size else 0
        print(f"\n  Latest build : {build.filename}")
        if build.version:
            print(f"  Version      : LineageOS {build.version}")
        if build.size:
            print(f"  Size         : {size_mib} MiB")
        if build.sha256:
            print(f"  SHA-256      : {build.sha256}")
        print()

        if ask_confirm(
            f"  Download {size_mib} MiB to {Path.cwd()} now? (verifies SHA-256)",
            default=False,
        ):
            print(f"\n  Downloading {build.filename} — this may take several minutes…")

            def _progress(read: int, total: int) -> None:
                if total <= 0:
                    sys.stderr.write(f"\r  downloaded {read // (1024 * 1024)} MiB")
                else:
                    pct = (read * 100) // total
                    sys.stderr.write(
                        f"\r  {read // (1024 * 1024)}/{total // (1024 * 1024)} MiB "
                        f"({pct}%)"
                    )
                sys.stderr.flush()

            try:
                downloaded_path = download_lineage_zip(
                    build, Path.cwd(), progress=_progress
                )
                sys.stderr.write("\n")
            except DistroFetchError as exc:
                sys.stderr.write("\n")
                print(f"{RED}  Download failed: {exc}{RESET}")

    print()
    print(render_download_options(
        codename=codename,
        build=build,
        page_url=page_url,
        alt_links=alt,
        api_error=api_error,
        downloaded_path=downloaded_path,
        network_skipped=False,
    ))
    input("\n  Press Enter to go back...")
    return "flash"


def _screen_flash_verify(ctx: WizardContext) -> str:
    import zipfile
    from ..flash import parse_rom_metadata, render_verify_result

    clear_screen()
    _header("Verify a ROM zip")

    path_str = ask_text("  Path to ROM zip")
    if not path_str:
        return "flash"
    zip_path = Path(path_str.strip()).expanduser()
    if not zip_path.exists():
        print(f"\n{RED}  File not found: {zip_path}{RESET}")
        input("\n  Press Enter to go back...")
        return "flash"

    valid = False
    try:
        with zipfile.ZipFile(zip_path):
            valid = True
    except zipfile.BadZipFile:
        pass

    metadata = parse_rom_metadata(zip_path) if valid else None
    codename = ""
    if not ctx.offline:
        try:
            codename = ctx.get_facts().codename
        except Exception:
            pass

    print()
    print(render_verify_result(zip_path, valid, metadata, codename))
    input("\n  Press Enter to go back...")
    return "flash"


def _screen_flash_run(ctx: WizardContext, fctx) -> str:
    from ..adb import Adb
    from ..flash import (
        DeviceState,
        Heimdall,
        Manufacturer,
        build_flash_plan,
        execute_flash_plan,
        heimdall_available,
        is_ab_device,
        render_flash_plan,
        render_flash_result,
    )

    clear_screen()
    _header("Flash a ROM")
    print(f"  {RED}⚠  This will OVERWRITE partitions on your device.{RESET}")
    print(f"  {RED}⚠  An interrupted flash can leave the device unbootable.{RESET}\n")

    rom_str = ask_text("  Path to ROM zip")
    if not rom_str:
        return "flash"
    rom_path = Path(rom_str.strip()).expanduser()
    if not rom_path.exists():
        print(f"\n{RED}  File not found: {rom_path}{RESET}")
        input("\n  Press Enter to go back...")
        return "flash"

    recovery_path = None
    if ask_confirm("  Also flash a custom recovery image?", default=False):
        rec_str = ask_text("  Path to recovery .img")
        if rec_str:
            recovery_path = Path(rec_str.strip()).expanduser()
            if not recovery_path.exists():
                print(f"\n{RED}  Recovery image not found: {recovery_path}{RESET}")
                input("\n  Press Enter to go back...")
                return "flash"

    from ..flash import parse_rom_metadata
    metadata = parse_rom_metadata(rom_path)
    if (
        metadata
        and fctx.codename
        and metadata.pre_device.lower() != fctx.codename.lower()
    ):
        print(f"\n{RED}  ⚠  This ROM targets {metadata.pre_device!r} but the connected "
              f"device is {fctx.codename!r}.{RESET}")
        print(f"{RED}  Flashing a ROM built for a different device can brick it.{RESET}")
        if not ask_confirm("  Flash anyway?", default=False):
            print("\n  Aborted — no changes made.")
            input("\n  Press Enter to go back...")
            return "flash"

    # fastboot getvar blocks until a fastboot device appears; only query it
    # in fastboot mode, and use ADB's slot suffix when booted.
    ab = False
    if fctx.state == DeviceState.FASTBOOT:
        try:
            ab = is_ab_device(fctx.fb.getvar("slot-count"))
        except Exception:
            pass
    elif fctx.state == DeviceState.BOOTED and fctx.target_adb is not None:
        try:
            ab = bool(fctx.target_adb.getprop("ro.boot.slot_suffix"))
        except Exception:
            pass

    hl = Heimdall() if fctx.manufacturer == Manufacturer.SAMSUNG else None
    hl_avail = heimdall_available() if fctx.manufacturer == Manufacturer.SAMSUNG else False

    plan = build_flash_plan(
        manufacturer=fctx.manufacturer,
        device_codename=fctx.codename,
        rom_path=rom_path,
        recovery_path=recovery_path,
        ab_device=ab,
        heimdall_available=hl_avail,
    )

    print()
    print(render_flash_plan(plan))

    if not ask_confirm(
        "  Proceed with this plan? (last chance to abort)", default=False
    ):
        print("\n  Aborted — no changes made.")
        input("\n  Press Enter to go back...")
        return "flash"
    if not ask_confirm(
        f"  {RED}Really flash {rom_path.name}? This will modify partitions.{RESET}",
        default=False,
    ):
        print("\n  Aborted — no changes made.")
        input("\n  Press Enter to go back...")
        return "flash"

    target_adb = fctx.target_adb if fctx.target_adb is not None else Adb()
    result = execute_flash_plan(
        plan,
        adb=target_adb,
        fastboot=fctx.fb,
        heimdall=hl,
        confirm=True,
        dry_run=False,
    )
    print()
    print(render_flash_result(result))
    input("\n  Press Enter to go back...")
    return "flash"


# ── Router ────────────────────────────────────────────────────────────────────

def run_wizard(serial: Optional[str] = None) -> int:
    from ..adb import Adb, AdbNotFoundError

    ctx = WizardContext(serial=serial)

    try:
        adb = Adb()
        devices = adb.list_devices()
        ready = [d for d in devices if d.ready]
        if not ready:
            ctx.offline = True
        elif serial:
            ctx.serial = serial
        elif len(ready) == 1:
            ctx.serial = ready[0].serial
        else:
            _screen_splash(ctx)
            serials = [d.serial for d in ready]
            chosen = ask_select("Multiple devices connected. Choose one:", serials)
            if chosen is None:
                return 0
            ctx.serial = chosen
    except AdbNotFoundError:
        ctx.offline = True

    _screen_splash(ctx)

    route = "main"
    while route != "exit":
        if route == "main":
            route = _screen_main_menu(ctx)
        elif route == "audit":
            route = _screen_audit(ctx)
        elif route == "harden":
            route = _screen_harden(ctx)
        elif route == "bootstrap":
            route = _screen_bootstrap(ctx)
        elif route == "location":
            route = _screen_location(ctx)
        elif route == "camera":
            route = _screen_camera(ctx)
        elif route == "flash":
            route = _screen_flash(ctx)
        else:
            route = "main"

    clear_screen()
    print(f"\n  Thanks for using los-bootstrap v{__version__}. Stay degoogled.\n")
    return 0
