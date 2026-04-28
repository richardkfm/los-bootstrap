"""Render device facts + audit findings as text or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Optional

from .audit.models import AuditReport, Severity
from .device import DeviceFacts


SEV_GLYPH = {
    Severity.INFO: "·",
    Severity.OK: "✓",
    Severity.WARN: "!",
    Severity.HIGH: "✗",
}


def render_text(facts: DeviceFacts, report: Optional[AuditReport]) -> str:
    lines: list[str] = []
    lines.append("Device")
    lines.append("------")
    lines.append(f"  Serial          : {facts.serial or '(default)'}")
    lines.append(f"  Manufacturer    : {facts.manufacturer}")
    lines.append(f"  Model           : {facts.model}")
    lines.append(f"  Codename        : {facts.codename}")
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
        lines.append("--------------")
        if not report.findings:
            lines.append("  (no findings)")
        for f in report.findings:
            glyph = SEV_GLYPH[f.severity]
            lines.append(f"  [{glyph}] {f.severity.value.upper():4} {f.title}")
            lines.append(f"        id     : {f.check}")
            lines.append(f"        detail : {f.detail}")
            if f.recommendation:
                lines.append(f"        suggest: {f.recommendation}")
        if report.has_concerns():
            warn = len(report.by_severity(Severity.WARN))
            high = len(report.by_severity(Severity.HIGH))
            lines.append("")
            lines.append(f"  Summary: {high} high, {warn} warn.")
        else:
            lines.append("")
            lines.append("  Summary: no concerns flagged.")

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
