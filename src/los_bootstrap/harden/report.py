"""Render a HardenReport as human-readable text."""

from __future__ import annotations

from .._render_utils import partition_findings, wrap
from .models import HardenFinding, HardenReport, HardenStatus


_STATUS_GLYPH = {
    HardenStatus.PASS: "✓",
    HardenStatus.WARN: "!",
    HardenStatus.FAIL: "✗",
    HardenStatus.INFO: "·",
    HardenStatus.UNKNOWN: "?",
}

# Kept for interactive.py compatibility
_STATUS_LABEL = {
    HardenStatus.PASS: "PASS",
    HardenStatus.WARN: "WARN",
    HardenStatus.FAIL: "FAIL",
    HardenStatus.INFO: "INFO",
    HardenStatus.UNKNOWN: " ?? ",
}

_ACTIONABLE = {HardenStatus.FAIL, HardenStatus.WARN}
_PASSING = {HardenStatus.PASS}
_INFO = {HardenStatus.INFO, HardenStatus.UNKNOWN}


def _render_finding(f: HardenFinding) -> list[str]:
    glyph = _STATUS_GLYPH[f.status]
    lines: list[str] = []
    lines.append(f"  {glyph}  {f.title}")

    if f.status in _PASSING:
        return lines

    if f.why:
        lines.append(wrap(f.why, "     "))

    if f.fix_hint and f.status in _ACTIONABLE:
        lines.append("")
        lines.append(wrap(f"→ Fix: {f.fix_hint}", "     "))

    if f.tradeoff:
        lines.append(wrap(f"⚠  Tradeoff: {f.tradeoff}", "     "))

    return lines


def render_harden_report(report: HardenReport) -> str:
    lines: list[str] = []
    lines.append("Hardening checks")
    lines.append("────────────────")

    if not report.findings:
        lines.append("  (no findings)")
        return "\n".join(lines) + "\n"

    actionable, passing, info = partition_findings(
        report.findings,
        lambda f: f.status,
        _ACTIONABLE,
        _PASSING,
        _INFO,
    )

    if actionable:
        count = len(actionable)
        noun = "issue" if count == 1 else "issues"
        lines.append(f"\n  {count} {noun} to address")
        lines.append("  " + "─" * 22)
        for f in actionable:
            lines.append("")
            lines.extend(_render_finding(f))

    if passing:
        lines.append("\n  Passing checks")
        lines.append("  " + "─" * 14)
        for f in passing:
            lines.append("")
            lines.extend(_render_finding(f))

    if info:
        lines.append("\n  For your information")
        lines.append("  " + "─" * 20)
        for f in info:
            lines.append("")
            lines.extend(_render_finding(f))

    lines.append("")
    fails = len(report.by_status(HardenStatus.FAIL))
    warns = len(report.by_status(HardenStatus.WARN))
    if report.has_failures():
        total = fails + warns
        noun = "issue" if total == 1 else "issues"
        lines.append(f"  {total} {noun} need attention.")
    else:
        lines.append("  All checks passed.")

    return "\n".join(lines) + "\n"
