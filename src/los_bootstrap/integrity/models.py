"""Data models for device-integrity findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class IntegrityStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntegrityFinding:
    check_id: str
    title: str
    status: IntegrityStatus
    detail: str
    why: str
    tradeoff: str
    fix_hint: str


@dataclass(frozen=True)
class IntegrityReport:
    findings: tuple[IntegrityFinding, ...] = field(default_factory=tuple)

    def by_status(self, status: IntegrityStatus) -> tuple[IntegrityFinding, ...]:
        return tuple(f for f in self.findings if f.status == status)

    def has_failures(self) -> bool:
        return any(
            f.status in (IntegrityStatus.WARN, IntegrityStatus.FAIL) for f in self.findings
        )
