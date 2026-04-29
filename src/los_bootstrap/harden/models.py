"""Data models for hardening findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HardenStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HardenFinding:
    check_id: str      # short id, e.g. "dev.adb"
    title: str
    status: HardenStatus
    detail: str        # current observed state
    why: str           # why this matters (required by roadmap)
    tradeoff: str      # what the user gives up by hardening (required by roadmap)
    fix_hint: str      # human-readable steps to fix
    fix_command: Optional[str] = None  # adb shell command to apply the fix, or None


@dataclass(frozen=True)
class HardenReport:
    findings: tuple[HardenFinding, ...] = field(default_factory=tuple)

    def by_status(self, status: HardenStatus) -> tuple[HardenFinding, ...]:
        return tuple(f for f in self.findings if f.status == status)

    def has_failures(self) -> bool:
        return any(f.status in (HardenStatus.WARN, HardenStatus.FAIL) for f in self.findings)
