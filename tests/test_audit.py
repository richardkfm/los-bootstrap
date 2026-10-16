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
        form_factor="phone",
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


def _base_answers() -> dict[str, str]:
    return {
        "pm list packages com.google.android.gms": "",
        "pm list packages com.google.android.gsf": "",
        "pm list packages com.android.vending": "",
        "pm list packages com.google.android.apps.maps": "",
        "pm list packages com.google.android.gm": "",
        "pm list packages com.google.android.youtube": "",
        "pm list packages com.google.android.inputmethod.latin": "",
        "settings get global private_dns_mode": "off\n",
        "settings get global private_dns_specifier": "null\n",
        "settings get secure lockscreen.disabled": "0\n",
    }


def test_clean_degoogled_device_has_only_dns_concern():
    facts = _facts()
    adb = Adb(serial="S1", runner=_runner(_base_answers()))
    report = run_audit(adb, facts)

    by_check = {f.check: f for f in report.findings}
    assert by_check["gms.present"].severity == Severity.OK
    assert by_check["google.client_packages"].severity == Severity.OK
    assert by_check["adb.tcp"].severity == Severity.OK
    assert by_check["lockscreen.present"].severity == Severity.OK
    # Default LineageOS leaves Private DNS off; the audit flags it.
    assert by_check["dns.private"].severity == Severity.WARN


def test_private_dns_hostname_is_ok():
    answers = _base_answers()
    answers["settings get global private_dns_mode"] = "hostname\n"
    answers["settings get global private_dns_specifier"] = "dns.quad9.net\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_audit(adb, _facts())
    by_check = {f.check: f for f in report.findings}
    assert by_check["dns.private"].severity == Severity.OK
    assert "dns.quad9.net" in by_check["dns.private"].detail


def test_gms_present_and_adb_tcp_open_flag_concerns():
    facts = _facts(adb_tcp_port="5555")
    answers = _base_answers()
    answers["pm list packages com.google.android.gms"] = "package:com.google.android.gms\n"
    answers["pm list packages com.google.android.gsf"] = "package:com.google.android.gsf\n"
    answers["pm list packages com.android.vending"] = "package:com.android.vending\n"
    answers["dumpsys package com.google.android.gms"] = "    versionName=24.38.33 (190400-680848563)\n"
    answers["dumpsys package com.android.vending"] = "    versionName=42.6.21-31 [0] [PR] 671392713\n"
    answers["settings get secure lockscreen.disabled"] = "1\n"
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
    adb = Adb(serial="S1", runner=_runner(_base_answers()))
    report = run_audit(adb, facts)
    rom_finding = next(f for f in report.findings if f.check == "rom.lineage")
    assert rom_finding.severity == Severity.INFO
    assert "Not a LineageOS" in rom_finding.title


def _microg_answers() -> dict[str, str]:
    """/e/OS and LineageOS for microG: GmsCore, GsfProxy and the companion."""
    answers = _base_answers()
    answers["pm list packages com.google.android.gms"] = "package:com.google.android.gms\n"
    answers["pm list packages com.google.android.gsf"] = "package:com.google.android.gsf\n"
    answers["pm list packages com.android.vending"] = "package:com.android.vending\n"
    answers["dumpsys package com.google.android.gms"] = "    versionName=0.3.6.244735\n"
    answers["dumpsys package com.android.vending"] = "    versionName=0.3.6.244735\n"
    return answers


def test_microg_is_not_reported_as_google_services():
    adb = Adb(serial="S1", runner=_runner(_microg_answers()))
    by_check = {f.check: f for f in run_audit(adb, _facts()).findings}
    assert by_check["gms.present"].severity == Severity.INFO
    assert "microG" in by_check["gms.present"].title
    assert by_check["gsf.present"].severity == Severity.INFO
    assert by_check["google.client_packages"].severity == Severity.OK


def test_unreadable_gms_version_still_warns():
    answers = _base_answers()
    answers["pm list packages com.google.android.gms"] = "package:com.google.android.gms\n"
    answers["dumpsys package com.google.android.gms"] = ""
    adb = Adb(serial="S1", runner=_runner(answers))
    by_check = {f.check: f for f in run_audit(adb, _facts()).findings}
    assert by_check["gms.present"].severity == Severity.WARN


def test_eos_rom_is_named_eos():
    facts = _facts(
        is_lineage=False,
        lineage_version="4.3-a14-20260921678710-community-bluejay",
        eos_version="4.3",
        eos_channel="community",
    )
    adb = Adb(serial="S1", runner=_runner(_microg_answers()))
    rom_finding = next(f for f in run_audit(adb, facts).findings if f.check == "rom.lineage")
    assert rom_finding.title == "/e/OS detected (LineageOS-based)"
    assert "4.3" in rom_finding.detail
