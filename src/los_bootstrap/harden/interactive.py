"""Interactive hardening walk-through.

Walks through each finding, explains why it matters and what the tradeoff is,
then optionally applies the fix via ADB.

Mutation is gated: fixes only execute when `confirm=True`. Without confirm,
the command is printed for the user to run manually. This mirrors the
plan/apply pattern in Phase 2.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

from ..adb import Adb, AdbCommandError
from .models import HardenFinding, HardenReport, HardenStatus
from .report import _STATUS_GLYPH, _STATUS_LABEL


Prompter = Callable[[str], str]


def _display_finding(f: HardenFinding) -> None:
    glyph = _STATUS_GLYPH[f.status]
    label = _STATUS_LABEL[f.status]
    print(f"\n[{glyph}] {label}  {f.title}")
    print(f"    Why     : {f.why}")
    print(f"    Tradeoff: {f.tradeoff}")
    print(f"    State   : {f.detail}")
    if f.fix_hint and f.status not in (HardenStatus.PASS, HardenStatus.INFO):
        print(f"    Fix     : {f.fix_hint}")


def _apply_fix(adb: Adb, f: HardenFinding, dry_run: bool, confirm: bool) -> None:
    """Offer to apply f.fix_command, respecting dry_run and confirm gates."""
    if f.fix_command is None:
        print("    (no automatic fix available — follow the manual steps above)")
        return

    full_cmd = f"adb shell {f.fix_command}"
    if dry_run:
        print(f"    [dry-run] would run: {full_cmd}")
        return

    if not confirm:
        print(f"    To apply: {full_cmd}")
        print("    (re-run with --confirm to let los-bootstrap apply this for you)")
        return

    try:
        adb.shell(f.fix_command)
        print("    Applied.")
        if f.check_id == "dev.adb":
            print(
                "    Note: USB debugging is now off — this ADB session just "
                "ended.\n    Re-enable it in Developer options if you need "
                "adb again."
            )
    except AdbCommandError as exc:
        print(f"    Error applying fix: {exc}", file=sys.stderr)


def run_interactive(
    report: HardenReport,
    adb: Adb,
    confirm: bool = False,
    dry_run: bool = False,
    prompter: Optional[Prompter] = None,
) -> None:
    """Walk through each finding interactively, offering fixes where available."""
    if prompter is None:
        prompter = input

    actionable = [
        f for f in report.findings
        if f.status in (HardenStatus.WARN, HardenStatus.FAIL)
    ]
    # Applying the ADB fix severs our own connection, so offer it last —
    # everything after it would fail.
    actionable.sort(key=lambda f: f.check_id == "dev.adb")
    informational = [
        f for f in report.findings
        if f.status not in (HardenStatus.WARN, HardenStatus.FAIL)
    ]

    if not actionable:
        print("\nAll hardening checks passed. Nothing to do.")
        for f in informational:
            _display_finding(f)
        return

    print(f"\n{len(actionable)} finding(s) need attention. Press Ctrl-C to abort at any time.\n")

    for f in actionable:
        _display_finding(f)
        try:
            answer = prompter("    Apply fix? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return
        if answer == "y":
            _apply_fix(adb, f, dry_run=dry_run, confirm=confirm)

    if informational:
        print("\n── Informational ─────────────────────────────────────────")
        for f in informational:
            _display_finding(f)

    print()
