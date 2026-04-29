"""Location / maps integration — Phase 4.

Public surface:
    run_location_doctor(adb, facts) -> LocationReport
    render_location_report(report) -> str
    render_compat_matrix() -> str
"""

from __future__ import annotations

from .checks import run_location_doctor
from .compat import COMPAT_MATRIX, AppCompatEntry, CompatLevel
from .models import LocationFinding, LocationReport, LocationStatus
from .report import render_compat_matrix, render_location_report

__all__ = [
    "AppCompatEntry",
    "COMPAT_MATRIX",
    "CompatLevel",
    "LocationFinding",
    "LocationReport",
    "LocationStatus",
    "render_compat_matrix",
    "render_location_report",
    "run_location_doctor",
]
