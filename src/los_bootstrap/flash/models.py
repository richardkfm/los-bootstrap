"""Data models for the ROM flashing assistant (Phase 8)."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class DeviceState(enum.Enum):
    BOOTED = "booted"        # normal ADB mode
    FASTBOOT = "fastboot"    # fastboot / bootloader mode
    RECOVERY = "recovery"    # recovery mode (ADB sideload available)
    DOWNLOAD = "download"    # Samsung download mode (Heimdall / Odin)
    UNKNOWN = "unknown"


class Manufacturer(enum.Enum):
    GOOGLE = "google"
    ONEPLUS = "oneplus"
    MOTOROLA = "motorola"
    FAIRPHONE = "fairphone"
    SAMSUNG = "samsung"
    XIAOMI = "xiaomi"
    GENERIC = "generic"      # unrecognised; generic fastboot may work


class FlashStepKind(enum.Enum):
    ADB_REBOOT = "adb_reboot"           # adb reboot [target]
    ADB_SIDELOAD = "adb_sideload"       # adb sideload <zip>
    FASTBOOT_UNLOCK = "fastboot_unlock" # fastboot flashing unlock
    FASTBOOT_FLASH = "fastboot_flash"   # fastboot flash <partition> <image>
    FASTBOOT_REBOOT = "fastboot_reboot" # fastboot reboot [target]
    FASTBOOT_UPDATE = "fastboot_update" # fastboot update <zip> (A/B devices)
    HEIMDALL_FLASH = "heimdall_flash"   # heimdall flash --<PARTITION> <image>
    MANUAL = "manual"                   # no command — user must act


@dataclass(frozen=True)
class FlashStep:
    kind: FlashStepKind
    description: str
    command: Optional[str] = None   # display string only
    args: tuple[str, ...] = ()      # typed args passed to the executor
    is_destructive: bool = False
    guidance: Optional[str] = None  # extra prose printed for MANUAL steps


@dataclass
class FlashPlan:
    steps: list[FlashStep]
    manufacturer: Manufacturer
    device_codename: str
    rom_path: Optional[Path] = None
    recovery_path: Optional[Path] = None


@dataclass(frozen=True)
class RomMetadata:
    pre_device: str     # device codename the ROM targets
    post_build: str
    timestamp: str


@dataclass
class FlashResult:
    steps_ok: int = 0
    steps_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def had_errors(self) -> bool:
        return bool(self.errors)
