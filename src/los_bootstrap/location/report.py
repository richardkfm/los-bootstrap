"""Render location doctor findings and the app compatibility matrix as text."""

from __future__ import annotations

from .compat import COMPAT_MATRIX, CompatLevel
from .models import LocationReport, LocationStatus


_STATUS_GLYPH = {
    LocationStatus.PASS: "✓",
    LocationStatus.WARN: "!",
    LocationStatus.FAIL: "✗",
    LocationStatus.INFO: "·",
    LocationStatus.UNKNOWN: "?",
}

_STATUS_LABEL = {
    LocationStatus.PASS: "PASS",
    LocationStatus.WARN: "WARN",
    LocationStatus.FAIL: "FAIL",
    LocationStatus.INFO: "INFO",
    LocationStatus.UNKNOWN: " ?? ",
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


def render_location_report(report: LocationReport) -> str:
    lines: list[str] = []
    lines.append("Location stack doctor")
    lines.append("---------------------")

    if not report.findings:
        lines.append("  (no findings)")
        return "\n".join(lines) + "\n"

    for f in report.findings:
        glyph = _STATUS_GLYPH[f.status]
        label = _STATUS_LABEL[f.status]
        lines.append(f"  [{glyph}] {label}  {f.title}")
        lines.append(f"        id      : {f.check_id}")
        lines.append(f"        state   : {f.detail}")
        lines.append(f"        why     : {f.why}")
        lines.append(f"        tradeoff: {f.tradeoff}")
        if f.fix_hint and f.status not in (LocationStatus.PASS, LocationStatus.INFO):
            lines.append(f"        fix     : {f.fix_hint}")
        lines.append("")

    fails = len(report.by_status(LocationStatus.FAIL))
    warns = len(report.by_status(LocationStatus.WARN))
    if report.has_failures():
        lines.append(f"Summary: {fails} fail, {warns} warn — review findings above.")
    else:
        lines.append("Summary: location stack looks healthy.")

    return "\n".join(lines) + "\n"


def render_compat_matrix() -> str:
    lines: list[str] = []
    lines.append("App location compatibility on degoogled ROMs")
    lines.append("--------------------------------------------")
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
