"""Tests for location stack checks. ADB is fully mocked via injected runner."""

from __future__ import annotations

import pytest

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.device import DeviceFacts
from los_bootstrap.location import (
    COMPAT_MATRIX,
    CompatLevel,
    render_compat_matrix,
    render_location_report,
    run_location_doctor,
)
from los_bootstrap.location.checks import (
    check_location_enabled,
    check_microg_core,
    check_nlp_backends,
    check_real_gms_conflict,
    check_signature_spoofing,
)
from los_bootstrap.location.models import LocationReport, LocationStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def _facts(**overrides) -> DeviceFacts:
    base = dict(
        serial="S1",
        manufacturer="Google",
        model="Pixel 7",
        codename="panther",
        android_release="14",
        sdk="34",
        security_patch="2025-12-01",
        build_id="UQ1A.000000.000",
        build_fingerprint="fp",
        is_lineage=True,
        lineage_version="21.0",
        adb_tcp_port=None,
        form_factor="phone",
    )
    base.update(overrides)
    return DeviceFacts(**base)


def _runner(shell_answers: dict[str, str], pm_answers: dict[str, bool] | None = None):
    """Build a fake ADB runner.

    shell_answers: maps shell command string → stdout string
    pm_answers: maps package name → installed bool (for pm list packages calls)
    """
    pm = pm_answers or {}

    def run(argv):
        assert argv[0] == "adb"
        assert argv[1:3] == ["-s", "S1"]
        sub = argv[3]

        if sub == "shell":
            cmd = argv[4]
            # Handle pm list packages queries
            if cmd.startswith("pm list packages "):
                pkg = cmd.split(" ", 3)[3]
                if pkg in pm:
                    out = f"package:{pkg}\n" if pm[pkg] else ""
                    return AdbResult(0, out, "")
                return AdbResult(0, "", "")
            if cmd in shell_answers:
                return AdbResult(0, shell_answers[cmd], "")
            raise AssertionError(f"unexpected shell cmd: {cmd!r}")

        raise AssertionError(f"unexpected adb sub-command: {sub!r}")

    return run


def _base_shell() -> dict[str, str]:
    """Shell answers for a well-configured location stack."""
    return {
        "settings get secure location_enabled": "1\n",
        "pm dump org.microg.gms.core": "FAKE_PACKAGE_SIGNATURE granted\n",
    }


def _base_pm() -> dict[str, bool]:
    """PM answers for a device with microG + DejaVu, no real GMS."""
    return {
        "org.microg.gms.core": True,
        "com.google.android.gms": False,
        "org.microg.nlp.backend.ichnaea": False,
        "org.fitchfamily.android.dejavu": True,
        "org.microg.nlp.backend.apple": False,
        "org.openbmap.unifiedNlp": False,
        "org.microg.nlp.backend.nominatim": False,
    }


# ── check_location_enabled ────────────────────────────────────────────────────

def test_location_enabled_pass():
    adb = Adb(serial="S1", runner=_runner({"settings get secure location_enabled": "1\n"}))
    (f,) = list(check_location_enabled(adb, _facts()))
    assert f.status == LocationStatus.PASS
    assert "enabled" in f.title


def test_location_disabled_fail():
    adb = Adb(serial="S1", runner=_runner({"settings get secure location_enabled": "0\n"}))
    (f,) = list(check_location_enabled(adb, _facts()))
    assert f.status == LocationStatus.FAIL
    assert "disabled" in f.title


def test_location_enabled_fallback_providers():
    # Simulate Android < 9: location_enabled returns something other than 0/1
    shell = {
        "settings get secure location_enabled": "null\n",
        "settings get secure location_providers_allowed": "gps,network\n",
    }
    adb = Adb(serial="S1", runner=_runner(shell))
    (f,) = list(check_location_enabled(adb, _facts()))
    assert f.status == LocationStatus.PASS


def test_location_disabled_fallback_empty_providers():
    shell = {
        "settings get secure location_enabled": "null\n",
        "settings get secure location_providers_allowed": "\n",
    }
    adb = Adb(serial="S1", runner=_runner(shell))
    (f,) = list(check_location_enabled(adb, _facts()))
    assert f.status == LocationStatus.FAIL


# ── check_microg_core ─────────────────────────────────────────────────────────

def test_microg_installed_pass():
    pm = {"org.microg.gms.core": True}
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_microg_core(adb, _facts()))
    assert f.status == LocationStatus.PASS
    assert "installed" in f.title


def test_microg_not_installed_info():
    pm = {"org.microg.gms.core": False}
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_microg_core(adb, _facts()))
    assert f.status == LocationStatus.INFO
    assert "not installed" in f.title


# ── check_signature_spoofing ──────────────────────────────────────────────────

def test_sig_spoof_granted_pass():
    pm = {"org.microg.gms.core": True}
    shell = {"pm dump org.microg.gms.core": "FAKE_PACKAGE_SIGNATURE granted=true\n"}
    adb = Adb(serial="S1", runner=_runner(shell, pm))
    (f,) = list(check_signature_spoofing(adb, _facts()))
    assert f.status == LocationStatus.PASS
    assert "granted" in f.title


def test_sig_spoof_not_granted_warn():
    pm = {"org.microg.gms.core": True}
    shell = {"pm dump org.microg.gms.core": "some other permissions\n"}
    adb = Adb(serial="S1", runner=_runner(shell, pm))
    (f,) = list(check_signature_spoofing(adb, _facts()))
    assert f.status == LocationStatus.WARN
    assert "NOT granted" in f.title


def test_sig_spoof_microg_absent_info():
    pm = {"org.microg.gms.core": False}
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_signature_spoofing(adb, _facts()))
    assert f.status == LocationStatus.INFO
    assert f.check_id == "loc.sig_spoof"


# ── check_nlp_backends ────────────────────────────────────────────────────────

def test_nlp_backends_one_found_pass():
    pm = {
        "org.microg.nlp.backend.ichnaea": False,
        "org.fitchfamily.android.dejavu": True,
        "org.microg.nlp.backend.apple": False,
        "org.openbmap.unifiedNlp": False,
        "org.microg.nlp.backend.nominatim": False,
    }
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_nlp_backends(adb, _facts()))
    assert f.status == LocationStatus.PASS
    assert "1 installed" in f.title
    assert "dejavu" in f.detail.lower()


def test_nlp_backends_multiple_found():
    pm = {
        "org.microg.nlp.backend.ichnaea": True,
        "org.fitchfamily.android.dejavu": True,
        "org.microg.nlp.backend.apple": False,
        "org.openbmap.unifiedNlp": False,
        "org.microg.nlp.backend.nominatim": False,
    }
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_nlp_backends(adb, _facts()))
    assert f.status == LocationStatus.PASS
    assert "2 installed" in f.title


def test_nlp_backends_none_found_info():
    pm = {
        "org.microg.nlp.backend.ichnaea": False,
        "org.fitchfamily.android.dejavu": False,
        "org.microg.nlp.backend.apple": False,
        "org.openbmap.unifiedNlp": False,
        "org.microg.nlp.backend.nominatim": False,
    }
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_nlp_backends(adb, _facts()))
    assert f.status == LocationStatus.INFO
    assert "none" in f.title.lower()


# ── check_real_gms_conflict ───────────────────────────────────────────────────

def test_gms_absent_pass():
    pm = {"com.google.android.gms": False}
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_real_gms_conflict(adb, _facts()))
    assert f.status == LocationStatus.PASS


def test_gms_present_warn():
    pm = {"com.google.android.gms": True}
    adb = Adb(serial="S1", runner=_runner({}, pm))
    (f,) = list(check_real_gms_conflict(adb, _facts()))
    assert f.status == LocationStatus.WARN
    assert "conflict" in f.title.lower()


# ── Orchestrator ──────────────────────────────────────────────────────────────

def test_run_location_doctor_returns_report():
    adb = Adb(serial="S1", runner=_runner(_base_shell(), _base_pm()))
    report = run_location_doctor(adb, _facts())
    assert isinstance(report, LocationReport)
    ids = {f.check_id for f in report.findings}
    assert "loc.enabled" in ids
    assert "loc.microg_core" in ids
    assert "loc.sig_spoof" in ids
    assert "loc.nlp_backends" in ids
    assert "loc.gms_conflict" in ids


def test_healthy_stack_no_failures():
    adb = Adb(serial="S1", runner=_runner(_base_shell(), _base_pm()))
    report = run_location_doctor(adb, _facts())
    assert not report.has_failures()


def test_location_disabled_causes_failure():
    shell = dict(_base_shell())
    shell["settings get secure location_enabled"] = "0\n"
    adb = Adb(serial="S1", runner=_runner(shell, _base_pm()))
    report = run_location_doctor(adb, _facts())
    assert report.has_failures()


# ── Report rendering ──────────────────────────────────────────────────────────

def test_render_location_report_pass():
    adb = Adb(serial="S1", runner=_runner(_base_shell(), _base_pm()))
    report = run_location_doctor(adb, _facts())
    text = render_location_report(report)
    assert "Location stack doctor" in text
    assert "Passing checks" in text
    assert "Location stack looks healthy." in text


def test_render_location_report_failures():
    shell = dict(_base_shell())
    shell["settings get secure location_enabled"] = "0\n"
    pm = dict(_base_pm())
    pm["com.google.android.gms"] = True
    adb = Adb(serial="S1", runner=_runner(shell, pm))
    report = run_location_doctor(adb, _facts())
    text = render_location_report(report)
    assert "✗" in text   # FAIL glyph
    assert "!" in text   # WARN glyph
    assert "issues need attention" in text


def test_render_location_report_empty():
    report = LocationReport(findings=())
    text = render_location_report(report)
    assert "(no findings)" in text


# ── Compatibility matrix ──────────────────────────────────────────────────────

def test_compat_matrix_non_empty():
    assert len(COMPAT_MATRIX) > 0


def test_compat_matrix_all_valid_statuses():
    valid = set(CompatLevel)
    for entry in COMPAT_MATRIX:
        assert entry.status in valid, f"{entry.name} has invalid status {entry.status!r}"


def test_compat_matrix_names_non_empty():
    for entry in COMPAT_MATRIX:
        assert entry.name, "every compat entry must have a name"
        assert entry.summary, f"{entry.name} must have a summary"


def test_render_compat_matrix_contains_known_apps():
    text = render_compat_matrix()
    assert "OsmAnd" in text
    assert "Telegram" in text
    assert "Google Maps" in text
    assert "yes" in text
    assert "no" in text


def test_render_compat_matrix_has_legend():
    text = render_compat_matrix()
    assert "Status legend:" in text
    assert "gps-only" in text
    assert "partial" in text
