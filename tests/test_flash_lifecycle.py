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
    major_version,
    pick_update_candidates,
    render_first_boot_report,
    render_update_report,
    run_first_boot,
)
from los_bootstrap.flash.distros import LineageBuild

_DAY = 86400
_BASE = 1_700_000_000  # arbitrary reference epoch

# A real ro.build.fingerprint follows the AOSP shape
# brand/product/device:release/id/incremental:type/tags — LineageOS carries
# `lineage_<codename>` in the product segment and never starts with
# "LineageOS/". Fixtures must match what a device actually reports.
_LOS_FINGERPRINT = (
    "google/lineage_panther/panther:15/AP2A.250705.003/1234567:userdebug/test-keys"
)
_STOCK_FINGERPRINT = (
    "google/panther/panther:15/AP2A.250705.003/1234567:user/release-keys"
)


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
        build_fingerprint=_LOS_FINGERPRINT,
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
        filename=f"lineage-{version}-UNOFFICIAL-panther.zip",
        url=f"https://example.invalid/lineage-{version}-panther.zip",
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


def test_parse_build_date_utc_returns_none_for_unusable_input():
    assert _parse_build_date_utc("") is None
    assert _parse_build_date_utc("   ") is None
    assert _parse_build_date_utc("not-a-number") is None


# ---------------------------------------------------------------------------
# major_version / pick_update_candidates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("21.0", "21"),
        ("22", "22"),
        ("21.0-20240101-NIGHTLY-panther", "21"),
        ("", ""),
        (None, ""),
        ("lineage", ""),
    ],
)
def test_major_version_extracts_leading_major(raw, expected):
    assert major_version(raw) == expected


def test_pick_update_candidates_prefers_same_major_version():
    builds = [
        _build(_BASE + 10 * _DAY, version="22.0"),
        _build(_BASE + 2 * _DAY, version="21.0"),
        _build(_BASE - _DAY, version="21.0"),
    ]
    same, overall = pick_update_candidates("21.0", builds)
    assert same is not None and same.version == "21.0"
    assert same.datetime == _BASE + 2 * _DAY
    assert overall is not None and overall.version == "22.0"


def test_pick_update_candidates_ignores_builds_without_timestamps():
    same, overall = pick_update_candidates("21.0", [_build(0)])
    assert same is None and overall is None


def test_pick_update_candidates_without_same_major_returns_none_for_same():
    same, overall = pick_update_candidates("21.0", [_build(_BASE, version="22.0")])
    assert same is None
    assert overall is not None and overall.version == "22.0"


# ---------------------------------------------------------------------------
# evaluate_rom_update — `flash update`
# ---------------------------------------------------------------------------


def test_rom_update_not_lineageos():
    facts = _facts(is_lineage=False, lineage_version=None, build_date_utc=None)
    result = evaluate_rom_update(facts, _build(_BASE))
    assert result.state is RomUpdateState.NOT_LINEAGEOS


def test_rom_update_not_lineageos_reported_without_network():
    """The 'not LineageOS' verdict needs no API call, so --no-network must still give it."""
    facts = _facts(is_lineage=False, lineage_version=None)
    result = evaluate_rom_update(facts, None, lookup_performed=False)
    assert result.state is RomUpdateState.NOT_LINEAGEOS


def test_rom_update_unsupported_without_builds():
    result = evaluate_rom_update(_facts(), None)
    assert result.state is RomUpdateState.UNSUPPORTED


def test_rom_update_unverifiable_when_lookup_skipped():
    result = evaluate_rom_update(
        _facts(), None, lookup_performed=False, note="network lookup skipped"
    )
    assert result.state is RomUpdateState.UNVERIFIABLE
    assert result.note == "network lookup skipped"


@pytest.mark.parametrize("device_date", [None, 0])
def test_rom_update_unverifiable_missing_device_date(device_date):
    result = evaluate_rom_update(_facts(build_date_utc=device_date), _build(_BASE + _DAY))
    assert result.state is RomUpdateState.UNVERIFIABLE
    assert "ro.build.date.utc" in result.note


def test_rom_update_unverifiable_note_blames_the_api_when_the_api_is_at_fault():
    """A bad API timestamp must not be reported to the user as a device problem."""
    result = evaluate_rom_update(_facts(), _build(0))
    assert result.state is RomUpdateState.UNVERIFIABLE
    assert "LineageOS API" in result.note
    assert "ro.build.date.utc" not in result.note


def test_rom_update_outdated_reports_days_behind():
    result = evaluate_rom_update(_facts(), _build(_BASE + 3 * _DAY + 3600))
    assert result.state is RomUpdateState.OUTDATED
    assert result.days_behind == 3
    assert result.latest_version == "21.0"
    assert result.latest_build_date == _BASE + 3 * _DAY + 3600


def test_rom_update_outdated_for_a_build_less_than_a_day_newer():
    """Rounding to whole days first would call a newer build 'up to date'."""
    result = evaluate_rom_update(_facts(), _build(_BASE + 3600))
    assert result.state is RomUpdateState.OUTDATED
    assert result.days_behind == 0


def test_rom_update_up_to_date_when_same_or_newer():
    same = evaluate_rom_update(_facts(), _build(_BASE))
    assert same.state is RomUpdateState.UP_TO_DATE
    assert same.days_behind == 0
    newer = evaluate_rom_update(_facts(build_date_utc=_BASE + _DAY), _build(_BASE))
    assert newer.state is RomUpdateState.UP_TO_DATE
    assert newer.days_behind == 0


def test_rom_update_flags_major_upgrade_separately_from_staleness():
    """A 22.x build must not be reported as the 21.x device being N days behind."""
    result = evaluate_rom_update(
        _facts(),
        _build(_BASE, version="21.0"),
        _build(_BASE + 30 * _DAY, version="22.0"),
    )
    assert result.state is RomUpdateState.UP_TO_DATE
    assert result.major_upgrade_available
    assert result.upgrade_version == "22.0"


def test_rom_update_no_major_upgrade_on_same_version():
    result = evaluate_rom_update(
        _facts(), _build(_BASE, version="21.0"), _build(_BASE, version="21.0")
    )
    assert not result.major_upgrade_available


# ---------------------------------------------------------------------------
# evaluate_first_boot — `flash check`
# ---------------------------------------------------------------------------


def _probes(**overrides) -> FirstBootProbes:
    base = dict(
        verified_boot="", build_type="", slot_suffix="", gms_variant="none", failed=()
    )
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


def test_first_boot_real_fingerprint_passes():
    """A genuine LineageOS fingerprint must not be flagged."""
    fb = _by_id(evaluate_first_boot(_facts(), _probes()))["fb.fingerprint"]
    assert fb.status is FirstBootStatus.PASS


def test_first_boot_healthy_lineage_device_has_nothing_actionable():
    """The whole point of `flash check`: a clean flash reports clean."""
    report = evaluate_first_boot(
        _facts(), _probes(verified_boot="orange", build_type="userdebug", slot_suffix="_b")
    )
    assert report.actionable_count() == 0
    assert not report.has_failures()


def test_first_boot_spoofed_fingerprint_is_informational_not_actionable():
    """Stock-fingerprint spoofing is deliberate on many ROMs; it must not gate exit codes."""
    report = evaluate_first_boot(
        _facts(build_fingerprint=_STOCK_FINGERPRINT), _probes(verified_boot="green")
    )
    fb = _by_id(report)["fb.fingerprint"]
    assert fb.status is FirstBootStatus.INFO
    assert report.actionable_count() == 0


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


def test_first_boot_real_gms_warns():
    fb = _by_id(evaluate_first_boot(_facts(), _probes(gms_variant="gms")))["fb.gms"]
    assert fb.status is FirstBootStatus.WARN
    assert fb.fix_hint


def test_first_boot_microg_passes():
    """microG registers the real GMS package id by design — it is not a finding."""
    report = evaluate_first_boot(
        _facts(), _probes(gms_variant="microg", verified_boot="green")
    )
    assert _by_id(report)["fb.gms"].status is FirstBootStatus.PASS
    assert report.actionable_count() == 0


def test_first_boot_gms_absent_passes():
    fb = _by_id(evaluate_first_boot(_facts(), _probes()))["fb.gms"]
    assert fb.status is FirstBootStatus.PASS


def test_first_boot_gms_unknown_is_not_a_pass():
    fb = _by_id(evaluate_first_boot(_facts(), _probes(gms_variant="unknown")))["fb.gms"]
    assert fb.status is FirstBootStatus.UNKNOWN


def test_first_boot_build_type_info_present_and_absent():
    present = _by_id(evaluate_first_boot(_facts(), _probes(build_type="userdebug")))
    assert "fb.build_type" in present
    absent = _by_id(evaluate_first_boot(_facts(), _probes()))
    assert "fb.build_type" not in absent


def test_first_boot_failed_probes_are_reported():
    report = evaluate_first_boot(
        _facts(), _probes(failed=("ro.boot.verifiedbootstate",))
    )
    fb = _by_id(report)
    assert fb["fb.probes"].status is FirstBootStatus.UNKNOWN
    assert "ro.boot.verifiedbootstate" in fb["fb.probes"].detail
    assert fb["fb.verified_boot"].status is FirstBootStatus.UNKNOWN


def test_first_boot_unreadable_gms_probe_never_reports_a_clean_pass():
    """A probe that could not run must not read as 'no GMS installed'."""
    report = evaluate_first_boot(
        _facts(), _probes(failed=("com.google.android.gms",), gms_variant="unknown")
    )
    assert _by_id(report)["fb.gms"].status is FirstBootStatus.UNKNOWN
    assert "Clean first boot" not in render_first_boot_report(report)


def test_first_boot_exit_gate_counts_failures_only():
    clean = evaluate_first_boot(_facts(), _probes())
    assert not clean.has_failures()

    with_gms = evaluate_first_boot(_facts(), _probes(gms_variant="gms"))
    assert with_gms.has_warnings()
    assert not with_gms.has_failures()
    assert with_gms.actionable_count() == 1

    bad_boot = evaluate_first_boot(_facts(), _probes(verified_boot="red"))
    assert bad_boot.has_failures()


# ---------------------------------------------------------------------------
# collect_first_boot_probes / run_first_boot — fake ADB
# ---------------------------------------------------------------------------


class _FakeAdb:
    def __init__(
        self,
        props: dict,
        gms_version: str | None = None,
        raise_all: bool = False,
        raise_on_gms: bool = False,
    ):
        self._props = props
        self._gms_version = gms_version
        self._raise = raise_all
        self._raise_on_gms = raise_on_gms

    def getprop(self, key: str) -> str:
        if self._raise:
            raise RuntimeError("adb down")
        return self._props.get(key, "")

    def package_installed(self, package: str) -> bool:
        if self._raise or self._raise_on_gms:
            raise RuntimeError("adb down")
        return self._gms_version is not None

    def shell(self, command: str) -> str:
        if self._raise or self._raise_on_gms:
            raise RuntimeError("adb down")
        return f"    versionName={self._gms_version}\n"


def test_collect_first_boot_probes_reads_props():
    adb = _FakeAdb(
        {
            "ro.boot.verifiedbootstate": "green",
            "ro.build.type": "userdebug",
            "ro.boot.slot_suffix": "_b",
        },
        gms_version="24.30.11",
    )
    probes = collect_first_boot_probes(adb)
    assert probes.verified_boot == "green"
    assert probes.build_type == "userdebug"
    assert probes.slot_suffix == "_b"
    assert probes.gms_variant == "gms"
    assert probes.failed == ()


def test_collect_first_boot_probes_classifies_microg():
    adb = _FakeAdb({}, gms_version="0.3.6.244735")
    assert collect_first_boot_probes(adb).gms_variant == "microg"


def test_collect_first_boot_probes_records_total_adb_failure():
    probes = collect_first_boot_probes(_FakeAdb({}, raise_all=True))
    assert probes.verified_boot == ""
    assert probes.gms_variant == "unknown"
    assert "ro.boot.verifiedbootstate" in probes.failed
    assert "com.google.android.gms" in probes.failed


def test_collect_first_boot_probes_records_partial_failure():
    """Only the GMS probe fails — the props still read, but the gap is recorded."""
    adb = _FakeAdb({"ro.boot.verifiedbootstate": "green"}, raise_on_gms=True)
    probes = collect_first_boot_probes(adb)
    assert probes.verified_boot == "green"
    assert probes.failed == ("com.google.android.gms",)


def test_dead_device_never_reports_a_clean_first_boot():
    """A device that answered nothing must not produce a reassuring report."""
    report = run_first_boot(_FakeAdb({}, raise_all=True), _facts())
    rendered = render_first_boot_report(report)
    assert "Clean first boot" not in rendered
    assert "could not be" in rendered


def test_run_first_boot_uses_adb_probes():
    adb = _FakeAdb(
        {
            "ro.boot.verifiedbootstate": "green",
            "ro.build.type": "userdebug",
            "ro.boot.slot_suffix": "_b",
        },
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
    assert "Samsung" in guide
    assert "Xiaomi" in guide
    assert "adb backup" in guide


def test_backup_guide_uses_a_real_heimdall_command():
    """`heimdall backup` does not exist; dumping EFS is `heimdall dump`."""
    guide = backup_guide()
    assert "heimdall dump --partition EFS" in guide
    assert "heimdall backup" not in guide


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "result_kwargs,expected",
    [
        (dict(latest=_build(_BASE + 3 * _DAY)), "3 days behind"),
        (dict(latest=_build(_BASE)), "up to date"),
        (dict(latest=None), "No official LineageOS builds"),
    ],
)
def test_render_update_report_covers_states(result_kwargs, expected):
    facts = _facts()
    result = evaluate_rom_update(facts, result_kwargs["latest"])
    assert expected in render_update_report(facts, result, result_kwargs["latest"])


def test_render_update_report_not_lineageos():
    facts = _facts(is_lineage=False, lineage_version=None)
    result = evaluate_rom_update(facts, None)
    assert "not running LineageOS" in render_update_report(facts, result, None)


def test_render_update_report_unverifiable_shows_the_note():
    facts = _facts()
    result = evaluate_rom_update(
        facts, None, lookup_performed=False, note="network lookup skipped (--no-network)"
    )
    out = render_update_report(facts, result, None)
    assert "Could not verify ROM freshness" in out
    assert "--no-network" in out


def test_render_update_report_shows_api_error_and_page_url():
    facts = _facts()
    result = evaluate_rom_update(facts, None, lookup_performed=False, note="unreachable")
    out = render_update_report(
        facts,
        result,
        None,
        api_error="network error querying LineageOS API",
        page_url="https://download.lineageos.org/devices/panther/builds",
    )
    assert "LineageOS API unavailable" in out
    assert "download.lineageos.org/devices/panther" in out


def test_render_update_report_warns_about_major_upgrade_wipe():
    facts = _facts()
    result = evaluate_rom_update(
        facts, _build(_BASE, version="21.0"), _build(_BASE + _DAY, version="22.0")
    )
    out = render_update_report(facts, result, _build(_BASE, version="21.0"))
    assert "newer major version" in out
    assert "full data wipe" in out
    assert "flash backup" in out


def test_render_first_boot_report_clean_shows_pass_line():
    report = evaluate_first_boot(_facts(), _probes(verified_boot="green"))
    assert "Clean first boot" in render_first_boot_report(report)


def test_render_first_boot_report_lists_actionable_findings_with_fixes():
    report = evaluate_first_boot(_facts(), _probes(verified_boot="red"))
    out = render_first_boot_report(report)
    assert "1 issue needs attention" in out
    assert "→ Fix:" in out


def test_render_first_boot_report_handles_empty_findings():
    from los_bootstrap.flash.models import FirstBootReport

    assert "(no findings)" in render_first_boot_report(FirstBootReport(()))
