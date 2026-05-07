"""Render device facts + audit findings as text or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

from ._render_utils import partition_findings, wrap
from .audit.models import AuditReport, Severity
from .device import DeviceFacts


_SEV_GLYPH = {
    Severity.INFO: "·",
    Severity.OK: "✓",
    Severity.WARN: "!",
    Severity.HIGH: "✗",
}

_ACTIONABLE = {Severity.WARN, Severity.HIGH}
_PASSING = {Severity.OK}
_INFO = {Severity.INFO}


def render_text(facts: DeviceFacts, report: Optional[AuditReport]) -> str:
    lines: list[str] = []
    lines.append("Device")
    lines.append("──────")
    lines.append(f"  Serial          : {facts.serial or '(default)'}")
    lines.append(f"  Manufacturer    : {facts.manufacturer}")
    lines.append(f"  Model           : {facts.model}")
    lines.append(f"  Codename        : {facts.codename}")
    lines.append(f"  Form factor     : {facts.form_factor}")
    lines.append(f"  Android         : {facts.android_release} (SDK {facts.sdk})")
    lines.append(f"  Security patch  : {facts.security_patch}")
    lines.append(f"  Build ID        : {facts.build_id}")
    lines.append(
        f"  ROM             : "
        f"{'LineageOS ' + (facts.lineage_version or '') if facts.is_lineage else 'AOSP-derived'}"
    )

    if report is not None:
        lines.append("")
        lines.append("Audit findings")
        lines.append("──────────────")

        if not report.findings:
            lines.append("  (no findings)")
        else:
            actionable, passing, info = partition_findings(
                report.findings,
                lambda f: f.severity,
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
                    glyph = _SEV_GLYPH[f.severity]
                    lines.append("")
                    lines.append(f"  {glyph}  {f.title}")
                    if f.detail:
                        lines.append(wrap(f.detail, "     "))
                    if f.recommendation:
                        lines.append("")
                        lines.append(wrap(f"→ How to fix: {f.recommendation}", "     "))

            if passing:
                lines.append("\n  Passing checks")
                lines.append("  " + "─" * 14)
                for f in passing:
                    glyph = _SEV_GLYPH[f.severity]
                    lines.append(f"  {glyph}  {f.title}")

            if info:
                lines.append("\n  For your information")
                lines.append("  " + "─" * 20)
                for f in info:
                    glyph = _SEV_GLYPH[f.severity]
                    lines.append("")
                    lines.append(f"  {glyph}  {f.title}")
                    if f.detail:
                        lines.append(wrap(f.detail, "     "))

        lines.append("")
        if report.has_concerns():
            warn = len(report.by_severity(Severity.WARN))
            high = len(report.by_severity(Severity.HIGH))
            total = warn + high
            noun = "issue" if total == 1 else "issues"
            lines.append(f"  {total} {noun} need attention.")
        else:
            lines.append("  No concerns flagged.")

    return "\n".join(lines) + "\n"


def render_json(facts: DeviceFacts, report: Optional[AuditReport]) -> str:
    payload: dict = {"device": asdict(facts)}
    if report is not None:
        payload["audit"] = {
            "findings": [
                {
                    "check": f.check,
                    "title": f.title,
                    "severity": f.severity.value,
                    "detail": f.detail,
                    "recommendation": f.recommendation,
                }
                for f in report.findings
            ]
        }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
