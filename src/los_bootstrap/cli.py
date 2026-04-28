"""Command-line entry point for `los-bootstrap`.

Phase 1 commands:
    devices    list ADB-connected devices
    info       print device facts
    audit      run privacy/degoogle audit
    report     info + audit, text or --json
    recommend  print non-binding bootstrap recommendations
    version    print version
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import __version__
from .adb import Adb, AdbCommandError, AdbNotFoundError, AdbDevice
from .audit import run_audit
from .bootstrap import recommendations
from .device import collect as collect_device
from .logo import banner
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
    except AdbNotFoundError as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.stderr.write("Install Android platform-tools so `adb` is on PATH.\n")
        return 127
    except AdbCommandError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1

    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable; keeps mypy/type-checkers happy


if __name__ == "__main__":
    raise SystemExit(main())
