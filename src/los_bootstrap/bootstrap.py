"""Phase 1 bootstrap recommendations.

Phase 1 is non-binding: we surface suggestions derived from audit
findings. We do not install anything. Phase 2 turns this into an
applyable plan.
"""

from __future__ import annotations

from .audit.models import AuditReport, Severity


GENERIC_TIPS: tuple[str, ...] = (
    "Install F-Droid (https://f-droid.org) — verify the APK signature.",
    "Install Aurora Store from F-Droid for proprietary apps without a Google account.",
    "Set up a non-Google DNS (e.g. NextDNS, Quad9) under Settings > Network > Private DNS.",
    "Set automatic time/timezone source to NITZ-only or NTP, not Google.",
    "Disable connectivity check or point it at a non-Google endpoint if your ROM supports it.",
)


def recommendations(report: AuditReport) -> list[str]:
    """Map findings to short, actionable suggestions."""
    out: list[str] = []
    seen: set[str] = set()
    for finding in report.findings:
        if finding.severity in (Severity.WARN, Severity.HIGH) and finding.recommendation:
            if finding.check not in seen:
                out.append(f"[{finding.severity.value}] {finding.title}: {finding.recommendation}")
                seen.add(finding.check)
    out.append("--- general tips ---")
    out.extend(GENERIC_TIPS)
    return out
