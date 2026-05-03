"""Render flash status, plans, and results as human-readable text."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import (
    DeviceState,
    FlashPlan,
    FlashResult,
    FlashStepKind,
    Manufacturer,
    RomMetadata,
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
