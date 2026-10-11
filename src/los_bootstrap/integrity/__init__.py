"""Device integrity & app compatibility — Phase 12 (read-only surface).

Public surface:
    run_integrity_doctor(adb, facts, root=False) -> IntegrityReport
    render_integrity_report(report) -> str
    render_compat_matrix() -> str
    render_guide() -> str

The mutating `integrity install` path is intentionally not part of this
release; it lands in a separate change.
"""

from __future__ import annotations

from .checks import run_integrity_doctor
from .compat import COMPAT_MATRIX, AppCompatEntry, CompatLevel
from .guide import GUIDE_STEPS, WARNINGS
from .models import IntegrityFinding, IntegrityReport, IntegrityStatus
from .report import render_compat_matrix, render_guide, render_integrity_report

__all__ = [
    "AppCompatEntry",
    "COMPAT_MATRIX",
    "CompatLevel",
    "GUIDE_STEPS",
    "IntegrityFinding",
    "IntegrityReport",
    "IntegrityStatus",
    "WARNINGS",
    "render_compat_matrix",
    "render_guide",
    "render_integrity_report",
    "run_integrity_doctor",
]
