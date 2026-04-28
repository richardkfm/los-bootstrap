"""Tests for the planner."""

from __future__ import annotations

from pathlib import Path

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.plan import StepKind, build_plan, render_plan
from los_bootstrap.profiles import AppEntry, Profile, SettingEntry


def _runner(answers: dict[str, str]):
    def run(argv):
        assert argv[:4] == ["adb", "-s", "S1", "shell"], argv
        cmd = argv[4]
        if cmd not in answers:
            raise AssertionError(f"unexpected shell cmd: {cmd!r}")
        return AdbResult(0, answers[cmd], "")

    return run


def _sample_profile() -> Profile:
    return Profile(
        name="t",
        description="test profile",
        apps=(
            AppEntry(id="org.fdroid.fdroid", source="sideload", apk="F-Droid.apk"),
            AppEntry(id="net.osmand.plus", source="fdroid", note="offline maps"),
            AppEntry(id="com.aurora.store", source="aurora"),
        ),
        settings=(
            SettingEntry(
                namespace="global",
                key="private_dns_mode",
                value="hostname",
                note="DoT",
            ),
            SettingEntry(
                namespace="global",
                key="private_dns_specifier",
                value="dns.quad9.net",
            ),
        ),
    )


def test_plan_skips_installed_apps_and_already_set_settings(tmp_path):
    apk = tmp_path / "F-Droid.apk"
    apk.write_bytes(b"\x00")
    answers = {
        # F-Droid already installed → skip; OsmAnd missing → manual; Aurora missing → manual
        "pm list packages org.fdroid.fdroid": "package:org.fdroid.fdroid\n",
        "pm list packages net.osmand.plus": "",
        "pm list packages com.aurora.store": "",
        # private_dns_mode already correct → skip; specifier needs to change
        "settings get global private_dns_mode": "hostname\n",
        "settings get global private_dns_specifier": "old.example.\n",
    }
    adb = Adb(serial="S1", runner=_runner(answers))
    plan = build_plan(adb, _sample_profile(), apk_dir=tmp_path)

    by_target = {s.target: s for s in plan.steps}
    assert by_target["org.fdroid.fdroid"].kind == StepKind.SKIP
    assert by_target["net.osmand.plus"].kind == StepKind.MANUAL_INSTALL
    assert by_target["com.aurora.store"].kind == StepKind.MANUAL_INSTALL
    assert by_target["global.private_dns_mode"].kind == StepKind.SKIP
    assert by_target["global.private_dns_specifier"].kind == StepKind.SET_SETTING
    assert "settings put global private_dns_specifier dns.quad9.net" in (
        by_target["global.private_dns_specifier"].command or ""
    )


def test_plan_install_apk_when_apk_present(tmp_path):
    apk = tmp_path / "F-Droid.apk"
    apk.write_bytes(b"\x00")
    answers = {
        "pm list packages org.fdroid.fdroid": "",
        "pm list packages net.osmand.plus": "package:net.osmand.plus\n",
        "pm list packages com.aurora.store": "package:com.aurora.store\n",
        "settings get global private_dns_mode": "off\n",
        "settings get global private_dns_specifier": "null\n",
    }
    adb = Adb(serial="S1", runner=_runner(answers))
    plan = build_plan(adb, _sample_profile(), apk_dir=tmp_path)

    fdroid_step = next(s for s in plan.steps if s.target == "org.fdroid.fdroid")
    assert fdroid_step.kind == StepKind.INSTALL_APK
    assert fdroid_step.command is not None
    assert str(apk) in fdroid_step.command
    assert fdroid_step.missing_apk_path is None


def test_plan_install_apk_marked_missing_when_no_apk_dir():
    answers = {
        "pm list packages org.fdroid.fdroid": "",
        "pm list packages net.osmand.plus": "",
        "pm list packages com.aurora.store": "",
        "settings get global private_dns_mode": "off\n",
        "settings get global private_dns_specifier": "null\n",
    }
    adb = Adb(serial="S1", runner=_runner(answers))
    plan = build_plan(adb, _sample_profile(), apk_dir=None)
    fdroid_step = next(s for s in plan.steps if s.target == "org.fdroid.fdroid")
    assert fdroid_step.kind == StepKind.INSTALL_APK
    assert fdroid_step.command is None
    assert fdroid_step.missing_apk_path == "no --apk-dir provided"


def test_render_plan_includes_summary_counts(tmp_path):
    apk = tmp_path / "F-Droid.apk"
    apk.write_bytes(b"\x00")
    answers = {
        "pm list packages org.fdroid.fdroid": "",
        "pm list packages net.osmand.plus": "",
        "pm list packages com.aurora.store": "",
        "settings get global private_dns_mode": "off\n",
        "settings get global private_dns_specifier": "null\n",
    }
    adb = Adb(serial="S1", runner=_runner(answers))
    plan = build_plan(adb, _sample_profile(), apk_dir=tmp_path)
    text = render_plan(plan)
    assert "Profile: t" in text
    assert "Summary:" in text
    # 1 sideload + 2 settings = 3 executable, 2 manual, 0 skipped
    assert "3 to run" in text
    assert "2 manual" in text
