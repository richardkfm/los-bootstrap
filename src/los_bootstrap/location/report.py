"""Render location doctor findings and the app compatibility matrix as text."""

from __future__ import annotations

import textwrap

from .compat import COMPAT_MATRIX, CompatLevel
from .models import LocationFinding, LocationReport, LocationStatus


_STATUS_GLYPH = {
    LocationStatus.PASS: "✓",
    LocationStatus.WARN: "!",
    LocationStatus.FAIL: "✗",
    LocationStatus.INFO: "·",
    LocationStatus.UNKNOWN: "?",
}

_COMPAT_GLYPH = {
    CompatLevel.YES: "✓",
    CompatLevel.GPS_ONLY: "~",
    CompatLevel.PARTIAL: "~",
    CompatLevel.NO: "✗",
}

_COMPAT_LABEL = {
    CompatLevel.YES: "yes     ",
    CompatLevel.GPS_ONLY: "gps-only",
    CompatLevel.PARTIAL: "partial ",
    CompatLevel.NO: "no      ",
}

_ACTIONABLE = {LocationStatus.FAIL, LocationStatus.WARN}
_PASSING = {LocationStatus.PASS}
_INFO = {LocationStatus.INFO, LocationStatus.UNKNOWN}


def _wrap(text: str, indent: str, width: int = 72) -> str:
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)


def _render_finding(f: LocationFinding) -> list[str]:
    glyph = _STATUS_GLYPH[f.status]
    lines: list[str] = []
    lines.append(f"  {glyph}  {f.title}")

    if f.status in _PASSING:
        return lines

    if f.why:
        lines.append(_wrap(f.why, "     "))

    if f.fix_hint and f.status in _ACTIONABLE:
        lines.append("")
        lines.append(_wrap(f"→ Fix: {f.fix_hint}", "     ", width=72))

    if f.tradeoff:
        lines.append(_wrap(f"⚠  Tradeoff: {f.tradeoff}", "     ", width=72))

    return lines


def render_location_report(report: LocationReport) -> str:
    lines: list[str] = []
    lines.append("Location stack doctor")
    lines.append("─────────────────────")

    if not report.findings:
        lines.append("  (no findings)")
        return "\n".join(lines) + "\n"

    actionable = [f for f in report.findings if f.status in _ACTIONABLE]
    passing = [f for f in report.findings if f.status in _PASSING]
    info = [f for f in report.findings if f.status in _INFO]

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
    fails = len(report.by_status(LocationStatus.FAIL))
    warns = len(report.by_status(LocationStatus.WARN))
    if report.has_failures():
        total = fails + warns
        noun = "issue" if total == 1 else "issues"
        lines.append(f"  {total} {noun} need attention.")
    else:
        lines.append("  Location stack looks healthy.")

    return "\n".join(lines) + "\n"


def render_compat_matrix() -> str:
    lines: list[str] = []
    lines.append("App location compatibility on degoogled ROMs")
    lines.append("────────────────────────────────────────────")
    lines.append(f"  {'App':<24}  {'Status':<10}  Notes")
    lines.append(f"  {'-' * 24}  {'-' * 10}  {'-' * 5}")

    for entry in COMPAT_MATRIX:
        sym = _COMPAT_GLYPH[entry.status]
        label = _COMPAT_LABEL[entry.status]
        lines.append(f"  [{sym}] {entry.name:<22}  {label}  {entry.summary}")

    lines.append("")
    lines.append("Status legend:")
    lines.append("  [✓] yes      — works fully without GMS or microG")
    lines.append("  [~] gps-only — GPS works; network location absent or degraded")
    lines.append("  [~] partial  — needs microG for full location functionality")
    lines.append("  [✗] no       — will not work even with microG; needs real GMS")

    return "\n".join(lines) + "\n"
