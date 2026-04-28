"""Tests for audit checks. ADB is fully mocked via injected runner."""

from __future__ import annotations

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.audit import run_audit
from los_bootstrap.audit.models import Severity
from los_bootstrap.device import DeviceFacts


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
    )
    base.update(overrides)
    return DeviceFacts(**base)


def _runner(answers: dict[str, str]):
    """Build a runner that satisfies adb.shell(<cmd>) lookups."""

    def run(argv):
        # All callers are `adb -s S1 shell <command>`.
        assert argv[:4] == ["adb", "-s", "S1", "shell"], argv
        cmd = argv[4]
        if cmd not in answers:
            raise AssertionError(f"unexpected shell cmd: {cmd!r}")
        return AdbResult(0, answers[cmd], "")

    return run


def test_clean_degoogled_device_has_no_concerns():
    facts = _facts()
    answers = {
        "pm list packages com.google.android.gms": "",
        "pm list packages com.google.android.gsf": "",
        "pm list packages com.android.vending": "",
        "pm list packages com.google.android.apps.maps": "",
        "pm list packages com.google.android.gm": "",
        "pm list packages com.google.android.youtube": "",
        "pm list packages com.google.android.inputmethod.latin": "",
        "settings get secure lockscreen.disabled": "0\n",
    }
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_audit(adb, facts)

    assert not report.has_concerns()
    severities = {f.check: f.severity for f in report.findings}
    assert severities["gms.present"] == Severity.OK
    assert severities["google.client_packages"] == Severity.OK
    assert severities["adb.tcp"] == Severity.OK
    assert severities["lockscreen.present"] == Severity.OK


def test_gms_present_and_adb_tcp_open_flag_concerns():
    facts = _facts(adb_tcp_port="5555")
    answers = {
        "pm list packages com.google.android.gms": "package:com.google.android.gms\n",
        "pm list packages com.google.android.gsf": "package:com.google.android.gsf\n",
        "pm list packages com.android.vending": "package:com.android.vending\n",
        "pm list packages com.google.android.apps.maps": "",
        "pm list packages com.google.android.gm": "",
        "pm list packages com.google.android.youtube": "",
        "pm list packages com.google.android.inputmethod.latin": "",
        "settings get secure lockscreen.disabled": "1\n",
    }
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_audit(adb, facts)

    assert report.has_concerns()
    by_check = {f.check: f for f in report.findings}
    assert by_check["gms.present"].severity == Severity.WARN
    assert by_check["gsf.present"].severity == Severity.WARN
    assert by_check["adb.tcp"].severity == Severity.HIGH
    assert by_check["lockscreen.present"].severity == Severity.HIGH
    assert by_check["google.client_packages"].severity == Severity.WARN


def test_non_lineage_rom_emits_info_finding():
    facts = _facts(is_lineage=False, lineage_version=None)
    answers = {
        "pm list packages com.google.android.gms": "",
        "pm list packages com.google.android.gsf": "",
        "pm list packages com.android.vending": "",
        "pm list packages com.google.android.apps.maps": "",
        "pm list packages com.google.android.gm": "",
        "pm list packages com.google.android.youtube": "",
        "pm list packages com.google.android.inputmethod.latin": "",
        "settings get secure lockscreen.disabled": "0",
    }
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_audit(adb, facts)
    rom_finding = next(f for f in report.findings if f.check == "rom.lineage")
    assert rom_finding.severity == Severity.INFO
    assert "Not a LineageOS" in rom_finding.title
