"""Enriched finding display helpers used by the wizard and --verbose flag.

These functions are additive — they do not replace the existing renderers in
report.py, harden/report.py, or location/report.py. They are called when the
user requests more context (wizard screens, --verbose CLI flag).
"""

from __future__ import annotations

import textwrap
from typing import Any

from .prose import FindingProse, get_prose


def _wrap(text: str, indent: str, width: int = 72) -> str:
    return textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)


def render_finding_detail(check_id: str, title: str) -> str:
    """Return a full prose detail block for a single finding."""
    prose = get_prose(check_id)
    lines: list[str] = []
    lines.append(f"  {title}")
    lines.append("  " + "─" * min(len(title), 68))
    lines.append("")

    if prose is None:
        lines.append("  (no extended prose available for this finding)")
        return "\n".join(lines) + "\n"

    lines.append("  WHAT'S HAPPENING")
    lines.append(_wrap(prose.what, "    "))
    lines.append("")

    if prose.common_causes:
        lines.append("  COMMON CAUSES")
        for part in prose.common_causes.split("\n"):
            lines.append(_wrap(part, "    ") if part.strip() else "")
        lines.append("")

    lines.append("  WHY IT MATTERS")
    lines.append(_wrap(prose.why, "    "))
    lines.append("")

    lines.append("  HOW TO FIX IT")
    for part in prose.fix.split("\n"):
        lines.append(_wrap(part, "    ") if part.strip() else "")
    lines.append("")

    lines.append("  TRADEOFF")
    lines.append(_wrap(prose.tradeoff, "    "))

    return "\n".join(lines) + "\n"


def render_verbose_audit(findings: Any) -> str:
    """Verbose rendering for audit findings (used with --verbose flag)."""
    from ..audit.models import Severity

    _GLYPH = {
        Severity.INFO: "·",
        Severity.OK: "✓",
        Severity.WARN: "!",
        Severity.HIGH: "✗",
    }

    _ACTIONABLE = {Severity.WARN, Severity.HIGH}
    _PASSING = {Severity.OK}

    lines: list[str] = []
    actionable = [f for f in findings if f.severity in _ACTIONABLE]
    passing = [f for f in findings if f.severity in _PASSING]
    info = [f for f in findings if f.severity not in _ACTIONABLE | _PASSING]

    if actionable:
        count = len(actionable)
        lines.append(f"\n  {count} {'issue' if count == 1 else 'issues'} to address")
        lines.append("  " + "─" * 22)
        for f in actionable:
            lines.append("")
            lines.append(render_finding_detail(f.check, f"{_GLYPH[f.severity]}  {f.title}"))

    if passing:
        lines.append("\n  Passing checks")
        lines.append("  " + "─" * 14)
        for f in passing:
            lines.append(f"  {_GLYPH[f.severity]}  {f.title}")

    if info:
        lines.append("\n  For your information")
        lines.append("  " + "─" * 20)
        for f in info:
            lines.append("")
            lines.append(render_finding_detail(f.check, f"{_GLYPH[f.severity]}  {f.title}"))

    return "\n".join(lines) + "\n"


def render_verbose_harden(findings: Any) -> str:
    """Verbose rendering for harden findings (used with --verbose flag)."""
    from ..harden.models import HardenStatus

    _GLYPH = {
        HardenStatus.PASS: "✓",
        HardenStatus.WARN: "!",
        HardenStatus.FAIL: "✗",
        HardenStatus.INFO: "·",
        HardenStatus.UNKNOWN: "?",
    }

    _ACTIONABLE = {HardenStatus.WARN, HardenStatus.FAIL}
    _PASSING = {HardenStatus.PASS}

    lines: list[str] = []
    actionable = [f for f in findings if f.status in _ACTIONABLE]
    passing = [f for f in findings if f.status in _PASSING]
    info = [f for f in findings if f.status not in _ACTIONABLE | _PASSING]

    if actionable:
        count = len(actionable)
        lines.append(f"\n  {count} {'issue' if count == 1 else 'issues'} to address")
        lines.append("  " + "─" * 22)
        for f in actionable:
            lines.append("")
            lines.append(render_finding_detail(f.check_id, f"{_GLYPH[f.status]}  {f.title}"))

    if passing:
        lines.append("\n  Passing checks")
        lines.append("  " + "─" * 14)
        for f in passing:
            lines.append(f"  {_GLYPH[f.status]}  {f.title}")

    if info:
        lines.append("\n  For your information")
        lines.append("  " + "─" * 20)
        for f in info:
            lines.append("")
            lines.append(render_finding_detail(f.check_id, f"{_GLYPH[f.status]}  {f.title}"))

    return "\n".join(lines) + "\n"
