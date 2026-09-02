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


# ---------------------------------------------------------------------------
# Phase 11 — flash lifecycle: ROM freshness + first-boot verification
# ---------------------------------------------------------------------------


class RomUpdateState(enum.Enum):
    UP_TO_DATE = "up_to_date"      # device build date >= latest official build
    OUTDATED = "outdated"          # a newer official build exists
    NOT_LINEAGEOS = "not_lineageos"  # device does not run LineageOS
    UNSUPPORTED = "unsupported"    # no official LOS builds for the codename
    UNVERIFIABLE = "unverifiable"  # could not compare (missing build date)


@dataclass(frozen=True)
class RomUpdateResult:
    state: RomUpdateState
    device_version: Optional[str] = None    # ro.lineage.version
    device_build_date: Optional[int] = None  # epoch seconds (ro.build.date.utc)
    latest_version: Optional[str] = None
    latest_build_date: Optional[int] = None
    days_behind: Optional[int] = None
    note: Optional[str] = None
    # Set when a newer LineageOS *major* version exists for this device.
    # Tracked separately from `state` because a major upgrade is not the same
    # errand as a nightly bump — it usually requires a full data wipe.
    upgrade_version: Optional[str] = None
    upgrade_build_date: Optional[int] = None

    @property
    def major_upgrade_available(self) -> bool:
        return self.upgrade_version is not None


class FirstBootStatus(enum.Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FirstBootProbes:
    """Device probes read by `run_first_boot` (all best-effort).

    `failed` names the probes that could not be read. Without it a device
    that stopped answering is indistinguishable from a clean one, and the
    report would claim a healthy first boot it never verified.
    """
    verified_boot: str = ""      # ro.boot.verifiedbootstate
    build_type: str = ""         # ro.build.type
    slot_suffix: str = ""        # ro.boot.slot_suffix (A/B)
    gms_variant: str = "none"    # "none" | "microg" | "gms" | "unknown"
    failed: tuple[str, ...] = ()  # probe names that raised

    def probe_failed(self, name: str) -> bool:
        return name in self.failed


@dataclass(frozen=True)
class FirstBootFinding:
    check_id: str    # e.g. "fb.lineage"
    title: str
    status: FirstBootStatus
    detail: str      # observed state
    why: str = ""    # why this matters
    fix_hint: str = ""


@dataclass
class FirstBootReport:
    findings: tuple[FirstBootFinding, ...] = field(default_factory=tuple)

    def by_status(self, status: FirstBootStatus) -> tuple[FirstBootFinding, ...]:
        return tuple(f for f in self.findings if f.status == status)

    def has_failures(self) -> bool:
        """True when a check actually failed (drives exit code 3)."""
        return any(f.status is FirstBootStatus.FAIL for f in self.findings)

    def has_warnings(self) -> bool:
        return any(f.status is FirstBootStatus.WARN for f in self.findings)

    def actionable_count(self) -> int:
        return sum(
            1 for f in self.findings
            if f.status in (FirstBootStatus.WARN, FirstBootStatus.FAIL)
        )
