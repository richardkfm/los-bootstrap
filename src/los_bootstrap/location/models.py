"""Data models for location stack findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LocationStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LocationFinding:
    check_id: str
    title: str
    status: LocationStatus
    detail: str
    why: str
    tradeoff: str
    fix_hint: str


@dataclass(frozen=True)
class LocationReport:
    findings: tuple[LocationFinding, ...] = field(default_factory=tuple)

    def by_status(self, status: LocationStatus) -> tuple[LocationFinding, ...]:
        return tuple(f for f in self.findings if f.status == status)

    def has_failures(self) -> bool:
        return any(f.status in (LocationStatus.WARN, LocationStatus.FAIL) for f in self.findings)
