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
        else:
            route = "main"

    clear_screen()
    print(f"\n  Thanks for using los-bootstrap v{__version__}. Stay degoogled.\n")
    return 0
