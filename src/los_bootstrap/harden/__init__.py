"""Hardening assistant — Phase 3.

Public surface:
    run_harden_checks(adb, facts, root=False) -> HardenReport
    render_harden_report(report) -> str
    run_interactive(report, adb, confirm, dry_run, prompter) -> None
"""

from .checks import run_harden_checks
from .interactive import run_interactive
from .models import HardenFinding, HardenReport, HardenStatus
from .report import render_harden_report

__all__ = [
    "HardenFinding",
    "HardenReport",
    "HardenStatus",
    "render_harden_report",
    "run_harden_checks",
    "run_interactive",
]
