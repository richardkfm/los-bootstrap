"""Tests for flash/lifecycle.py — ROM freshness + first-boot verification.

Pure evaluators take injected data; ADB IO is faked. No network, no device.
"""

from __future__ import annotations

import pytest

from los_bootstrap.device import DeviceFacts, _parse_build_date_utc
from los_bootstrap.flash import (
    FirstBootProbes,
    FirstBootStatus,
    RomUpdateState,
    backup_guide,
    collect_first_boot_probes,
    evaluate_first_boot,
    evaluate_rom_update,
    render_first_boot_report,
    render_update_report,
    run_first_boot,
)
from los_bootstrap.flash.distros import LineageBuild

_DAY = 86400
_BASE = 1_700_000_000  # arbitrary reference epoch


def _facts(**overrides) -> DeviceFacts:
    base = dict(
        serial="S1",
        manufacturer="Google",
        model="Pixel 7",
        codename="panther",
        android_release="15",
        sdk="35",
        security_patch="2025-12-01",
        build_id="AP2A.250705.003",
        build_fingerprint="LineageOS/21.0/user/panther/1234567/userdebug/test-keys",
        is_lineage=True,
        lineage_version="21.0",
        adb_tcp_port=None,
        form_factor="phone",
        build_date_utc=_BASE,
    )
    base.update(overrides)
    return DeviceFacts(**base)


def _build(latest_datetime: int, version: str = "21.0") -> LineageBuild:
    return LineageBuild(
        codename="panther",
        filename="lineage-21.0-UNOFFICIAL-panther.zip",
        url="https://example.invalid/lineage-21.0-panther.zip",
        size=1024,
        sha256="deadbeef",
        version=version,
        datetime=latest_datetime,
        build_type="nightly",
    )


# ---------------------------------------------------------------------------
# device._parse_build_date_utc
# ---------------------------------------------------------------------------


def test_parse_build_date_utc_parses_epoch_seconds():
    assert _parse_build_date_utc("1700000000") == 1700000000
    assert _parse_build_date_utc("  1700000000  ") == 1700000000


def test_parse_build_date_utc_empty_returns_none():
    assert _parse_build_date_utc("") is None
    assert _parse_build_date_utc("   ") is None


def test_parse_build_date_utc_garbage_returns_none():
    assert _parse_build_date_utc("not-a-date") is None


# ---------------------------------------------------------------------------
# evaluate_rom_update — `flash update`
# ---------------------------------------------------------------------------


def test_rom_update_not_lineageos():
    facts = _facts(is_lineage=False, lineage_version=None, build_date_utc=None)
    result = evaluate_rom_update(facts, _build(_BASE))
    assert result.state is RomUpdateState.NOT_LINEAGEOS


def test_rom_update_unsupported_without_builds():
    result = evaluate_rom_update(_facts(), None)
    assert result.state is RomUpdateState.UNSUPPORTED


@pytest.mark.parametrize("device_date", [None, 0])
def test_rom_update_unverifiable_missing_device_date(device_date):
    result = evaluate_rom_update(_facts(build_date_utc=device_date), _build(_BASE + _DAY))
    assert result.state is RomUpdateState.UNVERIFIABLE
    assert result.note


def test_rom_update_unverifiable_missing_latest_date():
    result = evaluate_rom_update(_facts(), _build(0))
    assert result.state is RomUpdateState.UNVERIFIABLE


def test_rom_update_outdated_reports_days_behind():
    result = evaluate_rom_update(_facts(), _build(_BASE + 3 * _DAY + 3600))
    assert result.state is RomUpdateState.OUTDATED
    assert result.days_behind == 3
    assert result.latest_version == "21.0"
    assert result.latest_build_date == _BASE + 3 * _DAY + 3600


def test_rom_update_up_to_date_when_same_or_newer():
    same = evaluate_rom_update(_facts(), _build(_BASE))
    assert same.state is RomUpdateState.UP_TO_DATE
    assert same.days_behind == 0
    newer = evaluate_rom_update(_facts(build_date_utc=_BASE + _DAY), _build(_BASE))
    assert newer.state is RomUpdateState.UP_TO_DATE
    assert newer.days_behind == 0


# ---------------------------------------------------------------------------
# evaluate_first_boot — `flash check`
# ---------------------------------------------------------------------------


def _probes(**overrides) -> FirstBootProbes:
    base = dict(verified_boot="", build_type="", slot_suffix="", gms_present=False)
    base.update(overrides)
    return FirstBootProbes(**base)


def _by_id(report) -> dict:
    return {f.check_id: f for f in report.findings}


def test_first_boot_lineage_detected_passes():
    fb = _by_id(evaluate_first_boot(_facts(), _probes()))
    assert fb["fb.lineage"].status is FirstBootStatus.PASS


def test_first_boot_not_lineage_fails():
    facts = _facts(is_lineage=False, lineage_version=None, build_fingerprint="")
    fb = _by_id(evaluate_first_boot(facts, _probes()))
    assert fb["fb.lineage"].status is FirstBootStatus.FAIL
    assert fb["fb.lineage"].fix_hint


@pytest.mark.parametrize("boot_state", ["green", "Orange"])
def test_first_boot_verified_boot_green_or_orange_passes(boot_state):
    fb = _by_id(evaluate_first_boot(_facts(), _probes(verified_boot=boot_state)))
    assert fb["fb.verified_boot"].status is FirstBootStatus.PASS


@pytest.mark.parametrize("boot_state", ["yellow", "red"])
def test_first_boot_verified_boot_yellow_or_red_fails(boot_state):
    fb = _by_id(evaluate_first_boot(_facts(), _probes(verified_boot=boot_state)))
    assert fb["fb.verified_boot"].status is FirstBootStatus.FAIL
    assert fb["fb.verified_boot"].fix_hint


def test_first_boot_verified_boot_unset_is_unknown():
    fb = _by_id(evaluate_first_boot(_facts(), _probes()))
    assert fb["fb.verified_boot"].status is FirstBootStatus.UNKNOWN


def test_first_boot_fingerprint_match_passes():
    fb = _by_id(evaluate_first_boot(_facts(), _probes()))
    assert fb["fb.fingerprint"].status is FirstBootStatus.PASS


def test_first_boot_fingerprint_mismatch_warns():
    fb = _by_id(evaluate_first_boot(_facts(build_fingerprint="sister/distro"), _probes()))
    assert fb["fb.fingerprint"].status is FirstBootStatus.WARN
    assert fb["fb.fingerprint"].fix_hint


def test_first_boot_fingerprint_info_when_not_lineage():
    facts = _facts(is_lineage=False, lineage_version=None, build_fingerprint="")
    fb = _by_id(evaluate_first_boot(facts, _probes()))
    assert fb["fb.fingerprint"].status is FirstBootStatus.INFO
    assert "(empty)" in fb["fb.fingerprint"].detail


def test_first_boot_ab_slot_vs_a_only():
    ab = _by_id(evaluate_first_boot(_facts(), _probes(slot_suffix="_b")))["fb.slot"]
    assert ab.status is FirstBootStatus.INFO
    assert ab.detail == "_b"
    a_only = _by_id(evaluate_first_boot(_facts(), _probes()))["fb.slot"]
    assert a_only.detail == "no ro.boot.slot_suffix set"


def test_first_boot_gms_present_warns():
    fb = _by_id(evaluate_first_boot(_facts(), _probes(gms_present=True)))["fb.gms"]
    assert fb.status is FirstBootStatus.WARN
    assert fb.fix_hint


def test_first_boot_gms_absent_passes():
    fb = _by_id(evaluate_first_boot(_facts(), _probes()))["fb.gms"]
    assert fb.status is FirstBootStatus.PASS


def test_first_boot_build_type_info_present_and_absent():
    present = _by_id(evaluate_first_boot(_facts(), _probes(build_type="userdebug")))
    assert "fb.build_type" in present
    absent = _by_id(evaluate_first_boot(_facts(), _probes()))
    assert "fb.build_type" not in absent


def test_first_boot_report_has_failures_on_warn_or_fail():
    clean = evaluate_first_boot(_facts(), _probes())
    assert not clean.has_failures()
    with_gms = evaluate_first_boot(_facts(), _probes(gms_present=True))
    assert with_gms.has_failures()
    assert len(with_gms.by_status(FirstBootStatus.WARN)) == 1


# ---------------------------------------------------------------------------
# collect_first_boot_probes / run_first_boot — fake ADB
# ---------------------------------------------------------------------------


class _FakeAdb:
    def __init__(
        self,
        props: dict,
        gms_present: bool = False,
        raise_all: bool = False,
    ):
        self._props = props
        self._gms = gms_present
        self._raise = raise_all

    def getprop(self, key: str) -> str:
        if self._raise:
            raise RuntimeError("adb down")
        return self._props.get(key, "")

    def package_installed(self, package: str) -> bool:
        if self._raise:
            raise RuntimeError("adb down")
        return self._gms


def test_collect_first_boot_probes_reads_props():
    adb = _FakeAdb(
        {
            "ro.boot.verifiedbootstate": "green",
            "ro.build.type": "userdebug",
            "ro.boot.slot_suffix": "_b",
        },
        gms_present=True,
    )
    probes = collect_first_boot_probes(adb)
    assert probes.verified_boot == "green"
    assert probes.build_type == "userdebug"
    assert probes.slot_suffix == "_b"
    assert probes.gms_present is True


def test_collect_first_boot_probes_survives_adb_errors():
    probes = collect_first_boot_probes(_FakeAdb({}, raise_all=True))
    assert probes.verified_boot == ""
    assert probes.build_type == ""
    assert probes.slot_suffix == ""
    assert probes.gms_present is False


def test_run_first_boot_uses_adb_probes():
    adb = _FakeAdb(
        {
            "ro.boot.verifiedbootstate": "green",
            "ro.build.type": "userdebug",
            "ro.boot.slot_suffix": "_b",
        },
        gms_present=False,
    )
    report = run_first_boot(adb, _facts())
    fb = _by_id(report)
    assert fb["fb.verified_boot"].status is FirstBootStatus.PASS
    assert fb["fb.gms"].status is FirstBootStatus.PASS
    assert not report.has_failures()


# ---------------------------------------------------------------------------
# backup_guide — static text
# ---------------------------------------------------------------------------


def test_backup_guide_covers_milestones_and_manufacturers():
    guide = backup_guide()
    assert "Pre-flash backup guidance" in guide
    assert "Milestone 1" in guide  # bootloader unlock wipes everything
    assert "Milestone 2" in guide  # ROM flash
    for note in ("Samsung", "Xiaomi", "Pixel"):
        assert note in guide
    assert "adb backup" in guide
    assert "flash check" in guide  # points at the post-flash follow-up


# ---------------------------------------------------------------------------
# renderers — smoke tests (plain text under pytest capture)
# ---------------------------------------------------------------------------


def test_render_update_report_outdated_shows_days_behind():
    facts = _facts()
    latest = _build(_BASE + 3 * _DAY + 3600)
    result = evaluate_rom_update(facts, latest)
    text = render_update_report(facts, result, latest)
    assert "ROM Freshness Check" in text
    assert "Your ROM is 3 days behind" in text


def test_render_first_boot_report_clean_shows_pass_line():
    facts = _facts()
    report = evaluate_first_boot(facts, _probes(verified_boot="green"))
    text = render_first_boot_report(report)
    assert "First-Boot Verification" in text
    assert "Clean first boot" in text