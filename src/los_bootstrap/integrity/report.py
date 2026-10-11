"""Render integrity findings, the compatibility matrix, and the guide as text."""

from __future__ import annotations

from datetime import date

from .._render_utils import paint, paint_glyph, partition_findings, wrap
from .compat import COMPAT_MATRIX, STALE_AFTER_DAYS, AppCompatEntry, CompatLevel
from .guide import GUIDE_STEPS, WARNINGS
from .models import IntegrityFinding, IntegrityReport, IntegrityStatus


_STATUS_GLYPH = {
    IntegrityStatus.PASS: "✓",
    IntegrityStatus.WARN: "!",
    IntegrityStatus.FAIL: "✗",
    IntegrityStatus.INFO: "·",
    IntegrityStatus.UNKNOWN: "?",
}

_ACTIONABLE = {IntegrityStatus.FAIL, IntegrityStatus.WARN}
_PASSING = {IntegrityStatus.PASS}
_INFO = {IntegrityStatus.INFO, IntegrityStatus.UNKNOWN}

_COMPAT_GLYPH = {
    CompatLevel.WORKS: "✓",
    CompatLevel.MICROG: "~",
    CompatLevel.SPOOF: "!",
    CompatLevel.BLOCKED: "✗",
    CompatLevel.UNKNOWN: "?",
}

_COMPAT_LABEL = {
    CompatLevel.WORKS: "works   ",
    CompatLevel.MICROG: "microG  ",
    CompatLevel.SPOOF: "spoof   ",
    CompatLevel.BLOCKED: "blocked ",
    CompatLevel.UNKNOWN: "unknown ",
}


def _render_finding(f: IntegrityFinding) -> list[str]:
    glyph = paint_glyph(_STATUS_GLYPH[f.status])
    lines = [f"  {glyph}  {f.title}"]
    if f.status in _PASSING:
        return lines
    if f.why:
        lines.append(wrap(f.why, "     "))
    if f.fix_hint and f.status in _ACTIONABLE:
        lines.append("")
        lines.append(wrap(f"→ Fix: {f.fix_hint}", "     "))
    if f.tradeoff and f.tradeoff not in ("None.", "N/A"):
        lines.append(wrap(f"⚠  Tradeoff: {f.tradeoff}", "     "))
    return lines


def render_integrity_report(report: IntegrityReport) -> str:
    lines = [paint("Device integrity doctor", "bold"), "───────────────────────"]
    lines.append(wrap(
        "These are the signals apps read before deciding whether to run. This "
        "tool cannot obtain a real Play Integrity verdict itself — that needs "
        "Google Play services and an app registered with Google. Use an "
        "on-device Play Integrity checker app for the actual verdict.",
        "  ",
    ))

    if not report.findings:
        lines.append("  (no findings)")
        return "\n".join(lines) + "\n"

    actionable, passing, info = partition_findings(
        report.findings, lambda f: f.status, _ACTIONABLE, _PASSING, _INFO
    )

    for title, bucket in (
        ("Likely to trip app checks", actionable),
        ("Passing checks", passing),
        ("For your information", info),
    ):
        if not bucket:
            continue
        lines.append(f"\n  {title}")
        lines.append("  " + "─" * len(title))
        for f in bucket:
            lines.append("")
            lines.extend(_render_finding(f))

    lines.append("")
    if report.has_failures():
        lines.append(paint(
            "  One or more signals are likely to trip app integrity checks. "
            "See `los-bootstrap integrity guide`.",
            "yellow",
        ))
    else:
        lines.append(paint("  No signals flagged. An app may still gate on a real verdict.", "green"))
    return "\n".join(lines) + "\n"


def _effective_level(entry: AppCompatEntry, today: date) -> CompatLevel:
    if entry.last_verified is None:
        return CompatLevel.UNKNOWN
    if (today - entry.last_verified).days > STALE_AFTER_DAYS:
        return CompatLevel.UNKNOWN
    return entry.status


def render_compat_matrix(today: date | None = None) -> str:
    today = today or date.today()
    lines = [
        "App compatibility on degoogled ROMs — Germany",
        "──────────────────────────────────────────────",
    ]
    for entry in COMPAT_MATRIX:
        level = _effective_level(entry, today)
        sym = _COMPAT_GLYPH[level]
        label = _COMPAT_LABEL[level]
        if entry.last_verified is None:
            age = "unverified"
        else:
            days = (today - entry.last_verified).days
            stale = " (stale)" if days > STALE_AFTER_DAYS else ""
            age = f"{entry.last_verified.isoformat()}{stale}"
        lines.append("")
        lines.append(f"  [{sym}] {entry.name:<24} {label}  verified: {age}")
        lines.append(wrap(entry.summary, "       "))
        lines.append(wrap(f"↪ Alternative: {entry.alternative}", "       "))
        lines.append(wrap(f"source: {entry.source}", "       "))

    lines.append("")
    lines.append("Status legend:")
    lines.append("  [✓] works   — runs on a degoogled ROM as-is")
    lines.append("  [~] microG  — runs once microG is installed; no verdict needed")
    lines.append("  [!] spoof   — needs Play Integrity spoofing (root)")
    lines.append("  [✗] blocked — no on-device workaround; use the alternative")
    lines.append("  [?] unknown — not reliably verified (or verification is stale)")
    lines.append("")
    lines.append(wrap(
        "An entry older than six months is shown as unknown on purpose: stale "
        "compatibility data is worse than none. Verified a status yourself? "
        "Open a PR.",
        "  ",
    ))
    return "\n".join(lines) + "\n"


def render_guide() -> str:
    lines = [paint("Making integrity-gated apps usable", "bold"), "──────────────────────────────────"]
    lines.append(wrap(
        "Ordered from lowest risk to highest. Try them in order; spoofing is "
        "the last resort, not the first.",
        "  ",
    ))
    for title, body in GUIDE_STEPS:
        lines.append("")
        lines.append(paint(f"  {title}", "cyan"))
        lines.append(wrap(body, "     "))

    lines.append("")
    lines.append(paint("  Before you spoof, read these", "bold"))
    lines.append("  " + "─" * 28)
    for title, body in WARNINGS:
        lines.append("")
        lines.append(wrap(f"⚠  {title}: {body}", "     "))
    return "\n".join(lines) + "\n"
