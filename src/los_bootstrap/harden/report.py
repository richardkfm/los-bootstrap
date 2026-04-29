"""Render a HardenReport as human-readable text."""

from __future__ import annotations

from .models import HardenReport, HardenStatus


_STATUS_GLYPH = {
    HardenStatus.PASS: "✓",
    HardenStatus.WARN: "!",
    HardenStatus.FAIL: "✗",
    HardenStatus.INFO: "·",
    HardenStatus.UNKNOWN: "?",
}

_STATUS_LABEL = {
    HardenStatus.PASS: "PASS",
    HardenStatus.WARN: "WARN",
    HardenStatus.FAIL: "FAIL",
    HardenStatus.INFO: "INFO",
    HardenStatus.UNKNOWN: " ?? ",
}


def render_harden_report(report: HardenReport) -> str:
    lines: list[str] = []
    lines.append("Hardening checks")
    lines.append("----------------")

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
        if f.fix_hint and f.status not in (HardenStatus.PASS, HardenStatus.INFO):
            lines.append(f"        fix     : {f.fix_hint}")
        lines.append("")

    fails = len(report.by_status(HardenStatus.FAIL))
    warns = len(report.by_status(HardenStatus.WARN))
    if report.has_failures():
        lines.append(f"Summary: {fails} fail, {warns} warn — review findings above.")
    else:
        lines.append("Summary: all checks passed.")

    return "\n".join(lines) + "\n"
