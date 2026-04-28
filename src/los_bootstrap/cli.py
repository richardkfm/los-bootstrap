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
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import __version__
from .adb import Adb, AdbCommandError, AdbNotFoundError, AdbDevice
from .apply import apply_plan
from .audit import run_audit
from .bootstrap import recommendations
from .device import collect as collect_device
from .logo import banner
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

    sub = parser.add_subparsers(dest="command", required=True)

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
        help="Directory containing APKs referenced by sideload steps.",
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

    return parser


def _print_banner(args: argparse.Namespace) -> None:
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
    plan = build_plan(adb, profile, apk_dir=apk_dir)
    print(render_plan(plan), end="")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    profile = find_profile(
        args.profile,
        extra_dirs=[Path(d) for d in args.profile_dir or []],
    )
    adb = _resolve_target(args.serial)
    apk_dir = Path(args.apk_dir) if args.apk_dir else None
    plan = build_plan(adb, profile, apk_dir=apk_dir)

    if not args.confirm and not args.dry_run:
        sys.stderr.write(render_plan(plan))
        sys.stderr.write(
            "\nrefusing to apply without --confirm. "
            "Re-run with `apply --profile ... --confirm` to execute, "
            "or add --dry-run to preview.\n"
        )
        return 2

    result = apply_plan(adb, plan, dry_run=args.dry_run)
    return 1 if result.had_errors() else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _print_banner(args)

    try:
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
    except AdbNotFoundError as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.stderr.write("Install Android platform-tools so `adb` is on PATH.\n")
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
