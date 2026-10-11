"""Device integrity & app compatibility — Phase 12.

Public surface:
    run_integrity_doctor(adb, facts, root=False) -> IntegrityReport
    render_integrity_report(report) -> str
    render_compat_matrix() -> str
    render_guide() -> str
    render_module_list() -> str
    run_install(adb, ...) -> InstallOutcome   # mutating; --root --confirm gated
"""

from __future__ import annotations

from .checks import run_integrity_doctor
from .compat import COMPAT_MATRIX, AppCompatEntry, CompatLevel
from .guide import GUIDE_STEPS, WARNINGS
from .install import InstallOutcome, run_install
from .models import IntegrityFinding, IntegrityReport, IntegrityStatus
from .modules import ModuleSource, find_module_source, load_module_sources
from .report import (
    render_compat_matrix,
    render_guide,
    render_integrity_report,
    render_module_list,
)

__all__ = [
    "AppCompatEntry",
    "COMPAT_MATRIX",
    "CompatLevel",
    "GUIDE_STEPS",
    "InstallOutcome",
    "IntegrityFinding",
    "IntegrityReport",
    "IntegrityStatus",
    "ModuleSource",
    "WARNINGS",
    "find_module_source",
    "load_module_sources",
    "render_compat_matrix",
    "render_guide",
    "render_integrity_report",
    "render_module_list",
    "run_install",
    "run_integrity_doctor",
]
