"""Tests for the applier."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.apply import apply_plan
from los_bootstrap.fetch import FetchError
from los_bootstrap.plan import Plan, PlanStep, StepKind


def _make_runner(record: list[list[str]], stdouts: dict[tuple[str, ...], str] | None = None):
    """A runner that records every argv it sees and replies with empty 0-rc."""
    stdouts = stdouts or {}

    def run(argv):
        record.append(list(argv))
        return AdbResult(0, stdouts.get(tuple(argv), ""), "")

    return run


def _plan(steps: tuple[PlanStep, ...]) -> Plan:
    return Plan(profile_name="t", description="", steps=steps)


def test_apply_runs_install_and_settings_in_order(tmp_path):
    apk = tmp_path / "f.apk"
    apk.write_bytes(b"\x00")

    plan = _plan(
        (
            PlanStep(
                kind=StepKind.INSTALL_APK,
                summary="sideload org.fdroid.fdroid",
                target="org.fdroid.fdroid",
                command=f"adb install -r {apk}",
            ),
            PlanStep(
                kind=StepKind.SET_SETTING,
                summary="set global.private_dns_mode = 'hostname'",
                target="global.private_dns_mode",
                command="adb shell settings put global private_dns_mode hostname",
            ),
            PlanStep(
                kind=StepKind.MANUAL_INSTALL,
                summary="install net.osmand.plus via F-Droid",
                target="net.osmand.plus",
            ),
            PlanStep(
                kind=StepKind.SKIP,
                summary="com.aurora.store already installed",
                target="com.aurora.store",
                skipped_reason="already present",
            ),
        )
    )

    record: list[list[str]] = []
    adb = Adb(serial="S1", runner=_make_runner(record))
    out = io.StringIO()
    result = apply_plan(adb, plan, out=out)

    # Two mutating adb invocations: install, then settings put.
    assert record == [
        ["adb", "-s", "S1", "install", "-r", str(apk)],
        [
            "adb",
            "-s",
            "S1",
            "shell",
            "settings put global private_dns_mode hostname",
        ],
    ]
    statuses = [r.status for r in result.results]
    assert statuses == ["ok", "ok", "manual", "skipped"]
    assert not result.had_errors()
    assert "Done:" in out.getvalue()


def test_apply_dry_run_executes_no_commands(tmp_path):
    apk = tmp_path / "f.apk"
    apk.write_bytes(b"\x00")
    plan = _plan(
        (
            PlanStep(
                kind=StepKind.INSTALL_APK,
                summary="sideload x",
                target="x",
                command=f"adb install -r {apk}",
            ),
            PlanStep(
                kind=StepKind.SET_SETTING,
                summary="set y",
                target="ns.y",
                command="adb shell settings put global y 1",
            ),
        )
    )
    record: list[list[str]] = []
    adb = Adb(serial="S1", runner=_make_runner(record))
    out = io.StringIO()
    result = apply_plan(adb, plan, dry_run=True, out=out)
    assert record == []
    assert all(r.status == "ok" for r in result.results)
    assert "dry run" in out.getvalue()


def test_apply_records_missing_apk_step(tmp_path):
    plan = _plan(
        (
            PlanStep(
                kind=StepKind.INSTALL_APK,
                summary="sideload x",
                target="x",
                command=None,
                missing_apk_path="no --apk-dir provided",
            ),
        )
    )
    record: list[list[str]] = []
    adb = Adb(serial="S1", runner=_make_runner(record))
    out = io.StringIO()
    result = apply_plan(adb, plan, out=out)
    assert record == []
    assert [r.status for r in result.results] == ["missing_apk"]


def test_apply_reports_install_failures():
    def failing_runner(argv):
        if argv[3] == "install":
            return AdbResult(1, "", "INSTALL_FAILED_INSUFFICIENT_STORAGE")
        return AdbResult(0, "", "")

    plan = _plan(
        (
            PlanStep(
                kind=StepKind.INSTALL_APK,
                summary="sideload x",
                target="x",
                command="adb install -r /tmp/x.apk",
            ),
        )
    )
    adb = Adb(serial="S1", runner=failing_runner)
    out = io.StringIO()
    result = apply_plan(adb, plan, out=out)
    assert result.had_errors()
    assert result.results[0].status == "error"
    assert "INSUFFICIENT_STORAGE" in result.results[0].detail


def test_apply_downloads_and_installs_apk(tmp_path):
    downloaded = tmp_path / "org.fdroid.fdroid_1010059.apk"
    step = PlanStep(
        kind=StepKind.INSTALL_APK,
        summary="download + install org.fdroid.fdroid",
        target="org.fdroid.fdroid",
        download_url="fdroid://org.fdroid.fdroid",
    )
    plan = _plan((step,))
    record: list[list[str]] = []
    adb = Adb(serial="S1", runner=_make_runner(record))
    out = io.StringIO()
    with patch("los_bootstrap.apply.fetch.download_apk", return_value=downloaded) as mock_dl:
        result = apply_plan(adb, plan, out=out, apk_dir=tmp_path)
    mock_dl.assert_called_once_with("fdroid://org.fdroid.fdroid", tmp_path)
    assert len(record) == 1
    assert record[0][3] == "install"
    assert result.results[0].status == "ok"


def test_apply_dry_run_skips_download():
    step = PlanStep(
        kind=StepKind.INSTALL_APK,
        summary="download + install org.fdroid.fdroid",
        target="org.fdroid.fdroid",
        download_url="fdroid://org.fdroid.fdroid",
    )
    plan = _plan((step,))
    record: list[list[str]] = []
    adb = Adb(serial="S1", runner=_make_runner(record))
    out = io.StringIO()
    with patch("los_bootstrap.apply.fetch.download_apk") as mock_dl:
        result = apply_plan(adb, plan, dry_run=True, out=out)
    mock_dl.assert_not_called()
    assert record == []
    assert result.results[0].status == "ok"


def test_apply_records_fetch_error_as_error(tmp_path):
    step = PlanStep(
        kind=StepKind.INSTALL_APK,
        summary="download + install com.example.app",
        target="com.example.app",
        download_url="https://example.com/app.apk",
    )
    plan = _plan((step,))
    record: list[list[str]] = []
    adb = Adb(serial="S1", runner=_make_runner(record))
    out = io.StringIO()
    with patch(
        "los_bootstrap.apply.fetch.download_apk",
        side_effect=FetchError("HTTP 404 downloading https://example.com/app.apk"),
    ):
        result = apply_plan(adb, plan, out=out, apk_dir=tmp_path)
    assert record == []
    assert result.results[0].status == "error"
    assert "404" in result.results[0].detail
