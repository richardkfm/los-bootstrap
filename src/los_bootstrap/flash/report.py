"""Render flash status, plans, and results as human-readable text."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .._render_utils import paint, paint_glyph, partition_findings, wrap
from ..device import DeviceFacts
from .distros import LineageBuild
from .models import (
    DeviceState,
    FirstBootFinding,
    FirstBootReport,
    FirstBootStatus,
    FlashPlan,
    FlashResult,
    FlashStepKind,
    Manufacturer,
    RomMetadata,
    RomUpdateResult,
    RomUpdateState,
)


_STATE_LABELS: dict[DeviceState, str] = {
    DeviceState.BOOTED: "booted (ADB)",
    DeviceState.FASTBOOT: "fastboot / bootloader mode",
    DeviceState.RECOVERY: "recovery mode",
    DeviceState.DOWNLOAD: "Samsung download mode",
    DeviceState.UNKNOWN: "unknown — no device detected",
}

_MFR_LABELS: dict[Manufacturer, str] = {
    Manufacturer.GOOGLE: "Google",
    Manufacturer.ONEPLUS: "OnePlus",
    Manufacturer.MOTOROLA: "Motorola",
    Manufacturer.FAIRPHONE: "Fairphone",
    Manufacturer.SAMSUNG: "Samsung",
    Manufacturer.XIAOMI: "Xiaomi / Redmi / POCO",
    Manufacturer.GENERIC: "Unknown / Generic",
}


def render_flash_status(
    state: DeviceState,
    manufacturer: Optional[Manufacturer],
    codename: str,
    bootloader_unlocked: Optional[bool] = None,
    dev_options: Optional[bool] = None,
    oem_unlocking: Optional[bool] = None,
) -> str:
    lines: list[str] = []
    lines.append("Flash Status")
    lines.append("════════════")
    lines.append(f"  Device state  : {_STATE_LABELS.get(state, state.value)}")

    if codename:
        lines.append(f"  Codename      : {codename}")
    if manufacturer is not None:
        lines.append(f"  Manufacturer  : {_MFR_LABELS.get(manufacturer, manufacturer.value)}")

    if dev_options is not None:
        lines.append(f"  Dev options   : {'enabled' if dev_options else 'DISABLED'}")
    if oem_unlocking is not None:
        lines.append(f"  OEM unlocking : {'enabled' if oem_unlocking else 'DISABLED'}")
    if bootloader_unlocked is not None:
        lines.append(
            f"  BL locked     : {'no (unlocked)' if bootloader_unlocked else 'YES (locked)'}"
        )

    lines.append("")
    return "\n".join(lines)


def render_flash_plan(plan: FlashPlan) -> str:
    lines: list[str] = []
    lines.append("Flash Plan")
    lines.append("══════════")
    lines.append(f"  Device    : {plan.device_codename or '(unknown)'}")
    lines.append(
        f"  Vendor    : {_MFR_LABELS.get(plan.manufacturer, plan.manufacturer.value)}"
    )
    if plan.rom_path:
        lines.append(f"  ROM       : {plan.rom_path}")
    if plan.recovery_path:
        lines.append(f"  Recovery  : {plan.recovery_path}")
    lines.append("")

    for i, step in enumerate(plan.steps, 1):
        destructive_tag = "  ⚠  DESTRUCTIVE" if step.is_destructive else ""
        manual_tag = "  [MANUAL]" if step.kind == FlashStepKind.MANUAL else ""
        lines.append(f"  {i:2d}. {step.description}{destructive_tag}{manual_tag}")
        if step.command:
            lines.append(f"      $ {step.command}")
        if step.guidance:
            for gline in step.guidance.splitlines():
                lines.append(f"      {gline}")

    lines.append("")
    return "\n".join(lines)


def render_verify_result(
    zip_path: Path,
    valid_zip: bool,
    metadata: Optional[RomMetadata],
    device_codename: str,
) -> str:
    lines: list[str] = []
    lines.append("ROM Verification")
    lines.append("════════════════")
    lines.append(f"  File   : {zip_path}")
    lines.append(f"  Zip    : {'valid' if valid_zip else 'INVALID — not a zip file'}")

    if not valid_zip:
        lines.append("")
        return "\n".join(lines)

    if metadata is None:
        lines.append("  Target : (no OTA metadata found — cannot verify device match)")
    else:
        lines.append(f"  Target : {metadata.pre_device}")
        if metadata.post_build:
            lines.append(f"  Build  : {metadata.post_build}")
        if device_codename:
            match = device_codename.lower() == metadata.pre_device.lower()
            status = "MATCH" if match else f"MISMATCH  (connected: {device_codename})"
            lines.append(f"  Match  : {status}")
            if not match:
                lines.append("")
                lines.append(
                    "  ⚠  The ROM targets a different device. Flashing the wrong ROM"
                )
                lines.append(
                    "     can brick the device. Verify you have the correct zip."
                )

    lines.append("")
    return "\n".join(lines)


def render_download_options(
    codename: str,
    build: Optional[LineageBuild],
    page_url: str,
    alt_links: list[tuple[str, str]],
    api_error: Optional[str] = None,
    downloaded_path: Optional[Path] = None,
    network_skipped: bool = False,
    show_fetch_hint: bool = True,
) -> str:
    lines: list[str] = []
    lines.append("ROM Download")
    lines.append("════════════")
    lines.append(f"  Codename : {codename or '(unknown)'}")
    lines.append("")

    lines.append("LineageOS")
    lines.append("─────────")
    if build is not None:
        lines.append(f"  Latest    : {build.filename}")
        if build.version:
            lines.append(f"  Version   : LineageOS {build.version}")
        if build.size:
            lines.append(f"  Size      : {_format_size(build.size)}")
        if build.sha256:
            lines.append(f"  SHA-256   : {build.sha256}")
        if build.url:
            lines.append(f"  URL       : {build.url}")
        if downloaded_path is not None:
            lines.append(f"  Saved to  : {downloaded_path}")
            lines.append("  → Verify  : SHA-256 matched.")
        elif show_fetch_hint:
            lines.append(
                "  → Re-run with --fetch to download and verify the zip."
            )
    elif network_skipped:
        lines.append(f"  Page      : {page_url}")
        lines.append("  → --no-network was set; drop it to fetch the latest build.")
    elif api_error:
        lines.append(f"  (LineageOS API unreachable: {api_error})")
        lines.append(f"  Page      : {page_url}")
    else:
        lines.append(
            "  No official LineageOS build found for this codename."
        )
        lines.append(f"  Page      : {page_url}")
        lines.append(
            "  → If your device is community-maintained, check the unofficial"
        )
        lines.append("    builds page or your device's XDA thread.")

    lines.append("")
    lines.append("Other distributions")
    lines.append("───────────────────")
    for name, url in alt_links:
        lines.append(f"  {name:22s} {url}")
    lines.append("")
    lines.append(
        "  ⚠  Always verify the SHA-256 of any ROM zip against the"
    )
    lines.append("     publisher's signed build manifest before flashing.")
    lines.append("")
    return "\n".join(lines)


def _format_size(num_bytes: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def render_flash_result(result: FlashResult) -> str:
    lines: list[str] = []
    lines.append("Flash Result")
    lines.append("════════════")
    lines.append(f"  Steps completed : {result.steps_ok}")
    lines.append(f"  Steps skipped   : {result.steps_skipped}")

    if result.errors:
        lines.append(f"  Errors          : {len(result.errors)}")
        for err in result.errors:
            lines.append(f"    • {err}")
    else:
        lines.append("  Errors          : none")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase 11 — flash lifecycle: ROM freshness + first-boot verification
# ---------------------------------------------------------------------------


def _format_build_date(epoch: Optional[int]) -> str:
    """Format an epoch-seconds timestamp as a UTC date; 'unknown' if unset."""
    if not epoch or epoch <= 0:
        return "unknown"
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")


def render_update_report(
    facts: DeviceFacts,
    result: RomUpdateResult,
    latest: Optional[LineageBuild],
    *,
    api_error: Optional[str] = None,
    page_url: Optional[str] = None,
) -> str:
    """Render the `flash update` ROM-freshness report."""
    lines: list[str] = []
    lines.append(paint("ROM Freshness Check", "bold"))
    lines.append("═════════════════════")
    lines.append(f"  Device    : {facts.model or '(unknown)'}")
    lines.append(f"  Codename  : {facts.codename or '(unknown)'}")
    if result.device_version:
        lines.append(
            f"  Running   : LineageOS {result.device_version} "
            f"(built {_format_build_date(result.device_build_date)})"
        )
    elif not facts.is_lineage:
        lines.append("  Running   : not a LineageOS build")
    if latest is not None and facts.is_lineage:
        lines.append(
            f"  Latest    : LineageOS {latest.version} "
            f"(built {_format_build_date(latest.datetime)})"
        )

    lines.append("")
    if result.state is RomUpdateState.UP_TO_DATE:
        lines.append(paint("  ✓ Your ROM is up to date", "green"))
    elif result.state is RomUpdateState.OUTDATED:
        days = result.days_behind or 0
        plural = "s" if days != 1 else ""
        if days == 0:
            lines.append(paint("  ✗ A newer build is available (less than a day)", "red"))
        else:
            lines.append(paint(f"  ✗ Your ROM is {days} day{plural} behind", "red"))
        lines.append(
            wrap(
                "Update with `los-bootstrap flash download "
                f"{facts.codename or '<codename>'}`, then re-flash with "
                "`los-bootstrap flash run <rom.zip> --confirm`.",
                "  ",
            )
        )
    elif result.state is RomUpdateState.NOT_LINEAGEOS:
        lines.append(paint("  ! This device is not running LineageOS", "yellow"))
        lines.append(
            wrap(
                "`flash update` tracks official LineageOS builds only. "
                "Sister distros (LineageOS for microG, /e/OS, DivestOS, "
                "etc.) publish on their own schedule — check their download "
                "pages instead.",
                "  ",
            )
        )
    elif result.state is RomUpdateState.UNSUPPORTED:
        lines.append(
            paint("  ! No official LineageOS builds for this codename", "yellow")
        )
        lines.append(
            wrap(
                "The LineageOS API reports no builds for "
                f"'{facts.codename or '(unknown)'}'. This device may run a "
                "sister distro, or its codename is not in the official list.",
                "  ",
            )
        )
    elif result.state is RomUpdateState.UNVERIFIABLE:
        lines.append(paint("  ! Could not verify ROM freshness", "yellow"))
        if result.note:
            lines.append(wrap(result.note + ".", "  "))
    else:
        lines.append(paint(f"  ! Unhandled result state: {result.state.value}", "yellow"))

    if api_error:
        lines.append("")
        lines.append(wrap(f"LineageOS API unavailable: {api_error}", "  "))
    if page_url:
        lines.append(wrap(f"Check manually: {page_url}", "  "))

    if result.major_upgrade_available:
        lines.append("")
        lines.append(
            paint(
                f"  ↑ A newer major version exists: LineageOS {result.upgrade_version} "
                f"(built {_format_build_date(result.upgrade_build_date)})",
                "cyan",
            )
        )
        lines.append(
            wrap(
                "⚠ Tradeoff: crossing a major version is not a routine "
                "update — it usually requires a full data wipe, and the "
                "upgrade path differs per device. Read `los-bootstrap flash "
                "backup` first and check the LineageOS wiki for your device.",
                "  ",
            )
        )

    lines.append("")
    return "\n".join(lines) + "\n"


_FB_GLYPH = {
    FirstBootStatus.PASS: "✓",
    FirstBootStatus.WARN: "!",
    FirstBootStatus.FAIL: "✗",
    FirstBootStatus.INFO: "·",
    FirstBootStatus.UNKNOWN: "?",
}

_FB_ACTIONABLE = {FirstBootStatus.FAIL, FirstBootStatus.WARN}
_FB_PASSING = {FirstBootStatus.PASS}
_FB_INFO = {FirstBootStatus.INFO, FirstBootStatus.UNKNOWN}


def _render_first_boot_finding(f: FirstBootFinding) -> list[str]:
    lines: list[str] = [f"  {paint_glyph(_FB_GLYPH[f.status])}  {f.title}"]

    if f.status not in _FB_PASSING and f.detail:
        lines.append(wrap(f.detail, "     "))

    if f.why:
        lines.append(wrap(f.why, "     "))

    # Hints are printed wherever they exist: a check that could not run
    # is bucketed as info, but "re-check the cable" is still the next step.
    if f.fix_hint:
        lines.append("")
        lines.append(wrap(f"→ Fix: {f.fix_hint}", "     "))

    return lines


def render_first_boot_report(report: FirstBootReport) -> str:
    """Render the `flash check` first-boot verification report."""
    lines: list[str] = []
    lines.append(paint("First-Boot Verification", "bold"))
    lines.append("─────────────────────────")

    if not report.findings:
        lines.append("  (no findings)")
        return "\n".join(lines) + "\n"

    actionable, passing, info = partition_findings(
        report.findings,
        lambda f: f.status,
        _FB_ACTIONABLE,
        _FB_PASSING,
        _FB_INFO,
    )

    if actionable:
        count = len(actionable)
        noun = "issue" if count == 1 else "issues"
        lines.append(f"\n  {count} {noun} to address")
        lines.append("  " + "─" * 22)
        for f in actionable:
            lines.append("")
            lines.extend(_render_first_boot_finding(f))

    if passing:
        lines.append("\n  Passing checks")
        lines.append("  " + "─" * 14)
        for f in passing:
            lines.append("")
            lines.extend(_render_first_boot_finding(f))

    if info:
        lines.append("\n  For your information")
        lines.append("  " + "─" * 20)
        for f in info:
            lines.append("")
            lines.extend(_render_first_boot_finding(f))

    lines.append("")
    total = report.actionable_count()
    unknowns = len(report.by_status(FirstBootStatus.UNKNOWN))
    if total:
        noun = "issue needs" if total == 1 else "issues need"
        color = "red" if report.has_failures() else "yellow"
        lines.append(paint(f"  {total} {noun} attention.", color))
    elif unknowns:
        lines.append(
            paint(
                "  No failures found, but some checks could not be completed.",
                "yellow",
            )
        )
    else:
        lines.append(paint("  Clean first boot — the install looks good.", "green"))

    return "\n".join(lines) + "\n"
