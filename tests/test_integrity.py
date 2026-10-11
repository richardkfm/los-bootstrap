"""Tests for the Phase 12 integrity doctor, compat matrix, and guide.

ADB is fully mocked via an injected runner; no real device is required.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.device import DeviceFacts
from los_bootstrap.integrity import (
    COMPAT_MATRIX,
    WARNINGS,
    CompatLevel,
    render_compat_matrix,
    render_guide,
    render_integrity_report,
    run_integrity_doctor,
)
from los_bootstrap.integrity.checks import PLAY_STORE_PACKAGE
from los_bootstrap.integrity.compat import STALE_AFTER_DAYS
from los_bootstrap.integrity.models import IntegrityStatus


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


def _runner(props: dict[str, str], settings: dict[str, str], installed: set[str]):
    def run(argv):
        assert argv[0] == "adb"
        assert argv[1:3] == ["-s", "S1"]
        assert argv[3] == "shell"
        cmd = argv[4]
        if cmd.startswith("getprop "):
            return AdbResult(0, props.get(cmd.split(" ", 1)[1], "") + "\n", "")
        if cmd.startswith("pm list packages "):
            pkg = cmd.split(" ", 3)[3]
            return AdbResult(0, f"package:{pkg}\n" if pkg in installed else "", "")
        if cmd.startswith("settings get "):
            key = cmd[len("settings get "):]
            return AdbResult(0, settings.get(key, "null") + "\n", "")
        raise AssertionError(f"unexpected shell cmd: {cmd!r}")

    return run


def _adb(props=None, settings=None, installed=None) -> Adb:
    return Adb(serial="S1", runner=_runner(props or {}, settings or {}, installed or set()))


# ── doctor ──────────────────────────────────────────────────────────────────

def test_unlocked_bootloader_warns():
    adb = _adb(props={"ro.boot.flash.locked": "0", "ro.boot.verifiedbootstate": "orange"})
    report = run_integrity_doctor(adb, _facts())
    boot = next(f for f in report.findings if f.check_id == "int.bootloader")
    assert boot.status is IntegrityStatus.WARN
    assert report.has_failures()


def test_locked_bootloader_passes():
    adb = _adb(props={"ro.boot.flash.locked": "1", "ro.boot.vbmeta.device_state": "locked"})
    report = run_integrity_doctor(adb, _facts())
    boot = next(f for f in report.findings if f.check_id == "int.bootloader")
    assert boot.status is IntegrityStatus.PASS


def test_test_keys_build_warns():
    adb = _adb(props={"ro.build.tags": "test-keys", "ro.boot.flash.locked": "1"})
    report = run_integrity_doctor(adb, _facts())
    keys = next(f for f in report.findings if f.check_id == "int.build_keys")
    assert keys.status is IntegrityStatus.WARN


def test_release_keys_build_is_info():
    adb = _adb(props={"ro.build.tags": "release-keys", "ro.boot.flash.locked": "1"})
    report = run_integrity_doctor(adb, _facts())
    keys = next(f for f in report.findings if f.check_id == "int.build_keys")
    assert keys.status is IntegrityStatus.INFO


def test_gms_classified_as_none_when_absent():
    adb = _adb(props={"ro.boot.flash.locked": "1"})
    report = run_integrity_doctor(adb, _facts())
    gms = next(f for f in report.findings if f.check_id == "int.gms")
    assert gms.status is IntegrityStatus.INFO
    assert "degoogled" in gms.title.lower()


def test_dev_options_enabled_warns():
    adb = _adb(
        props={"ro.boot.flash.locked": "1"},
        settings={"global development_settings_enabled": "1", "global adb_enabled": "1"},
    )
    report = run_integrity_doctor(adb, _facts())
    dev = next(f for f in report.findings if f.check_id == "int.dev_options")
    assert dev.status is IntegrityStatus.WARN


def test_root_check_only_runs_with_root_flag():
    adb = _adb(props={"ro.boot.flash.locked": "1"})
    assert all(f.check_id != "int.root" for f in run_integrity_doctor(adb, _facts()).findings)

    adb = _adb(props={"ro.boot.flash.locked": "1"}, installed={"com.topjohnwu.magisk"})
    report = run_integrity_doctor(adb, _facts(), root=True)
    root = next(f for f in report.findings if f.check_id == "int.root")
    assert "Magisk" in root.title


def test_doctor_handles_unreadable_props():
    adb = _adb()  # every getprop returns ""
    report = run_integrity_doctor(adb, _facts())
    boot = next(f for f in report.findings if f.check_id == "int.bootloader")
    assert boot.status is IntegrityStatus.UNKNOWN


# ── compat ────────────────────────────────────────────────────────────────────

def test_compat_renders_all_entries():
    out = render_compat_matrix()
    for entry in COMPAT_MATRIX:
        assert entry.name in out


def test_stale_entry_downgraded_to_unknown():
    latest = max((e.last_verified for e in COMPAT_MATRIX if e.last_verified), default=date.today())
    today = latest + timedelta(days=STALE_AFTER_DAYS + 1)
    out = render_compat_matrix(today=today)
    # A "today" past the freshness window makes every dated entry stale.
    assert "(stale)" in out


def test_unverified_entries_shown_as_unverified():
    out = render_compat_matrix()
    assert "unverified" in out


def test_every_entry_has_an_alternative():
    assert all(e.alternative.strip() for e in COMPAT_MATRIX)


# ── guide ─────────────────────────────────────────────────────────────────────

def test_guide_prints_all_three_warnings():
    out = render_guide()
    assert len(WARNINGS) == 3
    for title, _ in WARNINGS:
        assert title in out


def test_guide_lists_alternatives_before_spoofing():
    out = render_guide()
    assert out.index("route that is not the app") < out.index("Spoofing (last resort)")


def test_report_renders_without_error():
    adb = _adb(props={"ro.boot.flash.locked": "1", "ro.build.tags": "release-keys"})
    report = run_integrity_doctor(adb, _facts())
    assert "Device integrity doctor" in render_integrity_report(report)
