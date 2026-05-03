"""Build a FlashPlan from device facts and user-supplied file paths.

This module is read-only — it constructs a plan but does not execute it.
Execution lives in flash.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import (
    FlashPlan,
    FlashStep,
    FlashStepKind,
    Manufacturer,
)
from .guide import samsung_odin_guide


def build_flash_plan(
    manufacturer: Manufacturer,
    device_codename: str,
    rom_path: Path,
    recovery_path: Optional[Path] = None,
    ab_device: bool = False,
    heimdall_available: bool = False,
) -> FlashPlan:
    """Return a FlashPlan tailored to the manufacturer and partition layout."""
    steps: list[FlashStep]

    if manufacturer == Manufacturer.SAMSUNG:
        steps = _samsung_steps(rom_path, recovery_path, heimdall_available)
    elif manufacturer == Manufacturer.XIAOMI:
        steps = _xiaomi_steps(rom_path, recovery_path, ab_device)
    elif ab_device:
        steps = _ab_fastboot_steps(rom_path)
    else:
        steps = _aonly_fastboot_steps(rom_path, recovery_path)

    return FlashPlan(
        steps=steps,
        manufacturer=manufacturer,
        device_codename=device_codename,
        rom_path=rom_path,
        recovery_path=recovery_path,
    )


# ---------------------------------------------------------------------------
# Standard A-only fastboot path (Pixel A-only, OnePlus, Fairphone, Motorola,
# Xiaomi after unlock, generic)
# ---------------------------------------------------------------------------

def _aonly_fastboot_steps(
    rom_path: Path,
    recovery_path: Optional[Path],
) -> list[FlashStep]:
    steps: list[FlashStep] = []

    steps.append(FlashStep(
        kind=FlashStepKind.ADB_REBOOT,
        description="Reboot device to bootloader",
        command="adb reboot bootloader",
        args=("bootloader",),
    ))

    if recovery_path:
        steps.append(FlashStep(
            kind=FlashStepKind.FASTBOOT_FLASH,
            description=f"Flash recovery partition ({recovery_path.name})",
            command=f"fastboot flash recovery {recovery_path}",
            args=("recovery", str(recovery_path)),
        ))

    steps.append(FlashStep(
        kind=FlashStepKind.FASTBOOT_REBOOT,
        description="Reboot into recovery",
        command="fastboot reboot recovery",
        args=("recovery",),
    ))

    steps.append(FlashStep(
        kind=FlashStepKind.ADB_SIDELOAD,
        description=f"Sideload ROM ({rom_path.name})",
        command=f"adb sideload {rom_path}",
        args=(str(rom_path),),
    ))

    return steps


# ---------------------------------------------------------------------------
# A/B (seamless update) fastboot path — Pixel 3+, some OnePlus
# ---------------------------------------------------------------------------

def _ab_fastboot_steps(rom_path: Path) -> list[FlashStep]:
    steps: list[FlashStep] = []

    steps.append(FlashStep(
        kind=FlashStepKind.ADB_REBOOT,
        description="Reboot device to bootloader",
        command="adb reboot bootloader",
        args=("bootloader",),
    ))

    steps.append(FlashStep(
        kind=FlashStepKind.FASTBOOT_UPDATE,
        description=f"Flash ROM via fastboot update ({rom_path.name})",
        command=f"fastboot update {rom_path}",
        args=(str(rom_path),),
    ))

    return steps


# ---------------------------------------------------------------------------
# Samsung path via Heimdall (or Odin fallback)
# ---------------------------------------------------------------------------

def _samsung_steps(
    rom_path: Path,
    recovery_path: Optional[Path],
    heimdall_available: bool,
) -> list[FlashStep]:
    if not heimdall_available:
        return [
            FlashStep(
                kind=FlashStepKind.MANUAL,
                description="Flash recovery using Odin (Heimdall not installed)",
                guidance=samsung_odin_guide(),
            ),
            FlashStep(
                kind=FlashStepKind.ADB_SIDELOAD,
                description=f"Sideload ROM ({rom_path.name})",
                command=f"adb sideload {rom_path}",
                args=(str(rom_path),),
            ),
        ]

    steps: list[FlashStep] = []

    steps.append(FlashStep(
        kind=FlashStepKind.MANUAL,
        description="Enter Samsung Download Mode",
        guidance=(
            "  Power the device off, then enter Download Mode:\n"
            "  • With Home button:     Vol Down + Home + Power\n"
            "  • S8/S9/Note 8/9:      Vol Down + Bixby + Power\n"
            "  • S10 and later:       Vol Down + Vol Up → connect USB\n"
            "  Press Vol Up to accept the warning."
        ),
    ))

    if recovery_path:
        steps.append(FlashStep(
            kind=FlashStepKind.HEIMDALL_FLASH,
            description=f"Flash recovery partition ({recovery_path.name})",
            command=f"heimdall flash --RECOVERY {recovery_path}",
            args=("RECOVERY", str(recovery_path)),
        ))

    steps.append(FlashStep(
        kind=FlashStepKind.MANUAL,
        description="Boot into recovery IMMEDIATELY after Heimdall finishes",
        guidance=(
            "  Samsung restores stock recovery on the first normal Android boot.\n"
            "  As soon as Heimdall reports success, hold:\n"
            "  • With Home button:     Vol Up + Home + Power\n"
            "  • S8/S9/Note 8/9:      Vol Up + Bixby + Power\n"
            "  • S10 and later:       Vol Up + Power\n"
            "  until the LineageOS recovery screen appears."
        ),
    ))

    steps.append(FlashStep(
        kind=FlashStepKind.ADB_SIDELOAD,
        description=f"Sideload ROM ({rom_path.name})",
        command=f"adb sideload {rom_path}",
        args=(str(rom_path),),
    ))

    return steps


# ---------------------------------------------------------------------------
# Xiaomi path — standard fastboot after unlock
# ---------------------------------------------------------------------------

def _xiaomi_steps(
    rom_path: Path,
    recovery_path: Optional[Path],
    ab_device: bool,
) -> list[FlashStep]:
    # After the Mi Unlock Tool completes, Xiaomi devices work like standard
    # fastboot devices for the actual flash.
    steps: list[FlashStep] = [
        FlashStep(
            kind=FlashStepKind.MANUAL,
            description="Complete Xiaomi bootloader unlock before proceeding",
            guidance=(
                "  Run `los-bootstrap flash prepare` for the full Xiaomi\n"
                "  unlock guide, including the Mi account linking and the\n"
                "  mandatory 7–30 day waiting period."
            ),
        )
    ]
    if ab_device:
        steps.extend(_ab_fastboot_steps(rom_path))
    else:
        steps.extend(_aonly_fastboot_steps(rom_path, recovery_path))
    return steps
