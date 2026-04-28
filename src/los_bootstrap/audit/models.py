"""Data models for audit findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    INFO = "info"
    OK = "ok"
    WARN = "warn"
    HIGH = "high"


@dataclass(frozen=True)
class AuditFinding:
    check: str  # short id, e.g. "gms.present"
    title: str  # human-readable
    severity: Severity
    detail: str  # one-paragraph explanation
    recommendation: Optional[str] = None  # actionable hint for `recommend`


@dataclass(frozen=True)
class AuditReport:
    findings: tuple[AuditFinding, ...] = field(default_factory=tuple)

    def by_severity(self, sev: Severity) -> tuple[AuditFinding, ...]:
        return tuple(f for f in self.findings if f.severity == sev)

    def has_concerns(self) -> bool:
        return any(f.severity in (Severity.WARN, Severity.HIGH) for f in self.findings)
