"""Tests for hardening checks. ADB is fully mocked via injected runner."""

from __future__ import annotations

import pytest

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.device import DeviceFacts
from los_bootstrap.harden import run_harden_checks
from los_bootstrap.harden.checks import (
    check_adb_enabled,
    check_developer_options,
    check_encryption,
    check_lockdown_power_menu,
    check_screen_lock,
    check_selinux,
    check_unknown_sources,
    check_verified_boot,
)
from los_bootstrap.harden.interactive import run_interactive
from los_bootstrap.harden.models import HardenReport, HardenStatus
from los_bootstrap.harden.report import render_harden_report


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


def _runner(answers: dict[str, str]):
    def run(argv):
        assert argv[:4] == ["adb", "-s", "S1", "shell"], argv
        cmd = argv[4]
        if cmd not in answers:
            raise AssertionError(f"unexpected shell cmd: {cmd!r}")
        return AdbResult(0, answers[cmd], "")
    return run


def _base_answers() -> dict[str, str]:
    """Answers that represent a well-hardened device."""
    return {
        "settings get global development_settings_enabled": "0\n",
        "settings get global adb_enabled": "0\n",
        "settings get secure lockscreen.disabled": "0\n",
        "getprop ro.crypto.state": "encrypted\n",
        "getprop ro.crypto.type": "file\n",
        "settings get secure install_non_market_apps": "0\n",
        "getprop ro.boot.verifiedbootstate": "green\n",
        "settings get secure lockdown_mode_allowed": "1\n",
    }


# ── Non-root check tests ──────────────────────────────────────────────────────

def test_fully_hardened_device_all_pass():
    adb = Adb(serial="S1", runner=_runner(_base_answers()))
    report = run_harden_checks(adb, _facts())
    assert not report.has_failures()
    by_id = {f.check_id: f for f in report.findings}
    assert by_id["dev.options"].status == HardenStatus.PASS
    assert by_id["dev.adb"].status == HardenStatus.PASS
    assert by_id["sec.screen_lock"].status == HardenStatus.PASS
    assert by_id["sec.encryption"].status == HardenStatus.PASS
    assert by_id["sec.unknown_sources"].status == HardenStatus.PASS
    assert by_id["sec.verified_boot"].status == HardenStatus.PASS
    assert by_id["sec.lockdown_menu"].status == HardenStatus.PASS


def test_developer_options_enabled_is_warn():
    answers = _base_answers()
    answers["settings get global development_settings_enabled"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_developer_options(adb, _facts()))
    assert finding.status == HardenStatus.WARN
    assert "enabled" in finding.title


def test_adb_enabled_is_warn_and_has_fix_command():
    answers = _base_answers()
    answers["settings get global adb_enabled"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_adb_enabled(adb, _facts()))
    assert finding.status == HardenStatus.WARN
    assert finding.fix_command == "settings put global adb_enabled 0"


def test_screen_lock_disabled_is_fail():
    answers = _base_answers()
    answers["settings get secure lockscreen.disabled"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_screen_lock(adb, _facts()))
    assert finding.status == HardenStatus.FAIL
    assert finding.fix_command is None  # can't set credentials via ADB


def test_encryption_encrypted_file_is_pass():
    answers = _base_answers()
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_encryption(adb, _facts()))
    assert finding.status == HardenStatus.PASS
    assert "FBE" in finding.title


def test_encryption_unencrypted_is_fail():
    answers = _base_answers()
    answers["getprop ro.crypto.state"] = "unencrypted\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_encryption(adb, _facts()))
    assert finding.status == HardenStatus.FAIL


def test_unknown_sources_enabled_is_warn_with_fix():
    answers = _base_answers()
    answers["settings get secure install_non_market_apps"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_unknown_sources(adb, _facts()))
    assert finding.status == HardenStatus.WARN
    assert finding.fix_command == "settings put secure install_non_market_apps 0"


def test_verified_boot_green_is_pass():
    answers = _base_answers()
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_verified_boot(adb, _facts()))
    assert finding.status == HardenStatus.PASS
    assert "green" in finding.title


def test_verified_boot_orange_is_warn():
    answers = _base_answers()
    answers["getprop ro.boot.verifiedbootstate"] = "orange\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_verified_boot(adb, _facts()))
    assert finding.status == HardenStatus.WARN
    assert "orange" in finding.title


def test_verified_boot_red_is_fail():
    answers = _base_answers()
    answers["getprop ro.boot.verifiedbootstate"] = "red\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_verified_boot(adb, _facts()))
    assert finding.status == HardenStatus.FAIL


def test_lockdown_not_in_power_menu_is_warn():
    answers = _base_answers()
    answers["settings get secure lockdown_mode_allowed"] = "0\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    (finding,) = list(check_lockdown_power_menu(adb, _facts()))
    assert finding.status == HardenStatus.WARN
    assert finding.fix_command == "settings put secure lockdown_mode_allowed 1"


# ── Root check tests ──────────────────────────────────────────────────────────

def test_selinux_enforcing_is_pass():
    answers = {"su -c getenforce": "Enforcing\n"}
    def run(argv):
        assert argv[:4] == ["adb", "-s", "S1", "shell"], argv
        return AdbResult(0, answers[argv[4]], "")
    adb = Adb(serial="S1", runner=run)
    (finding,) = list(check_selinux(adb, _facts()))
    assert finding.status == HardenStatus.PASS


def test_selinux_permissive_is_fail():
    answers = {"su -c getenforce": "Permissive\n"}
    def run(argv):
        assert argv[:4] == ["adb", "-s", "S1", "shell"], argv
        return AdbResult(0, answers[argv[4]], "")
    adb = Adb(serial="S1", runner=run)
    (finding,) = list(check_selinux(adb, _facts()))
    assert finding.status == HardenStatus.FAIL
    assert "Permissive" in finding.detail


def test_root_checks_not_run_without_flag():
    adb = Adb(serial="S1", runner=_runner(_base_answers()))
    report = run_harden_checks(adb, _facts(), root=False)
    ids = {f.check_id for f in report.findings}
    assert "sec.selinux" not in ids


def test_root_checks_run_with_flag():
    answers = {**_base_answers(), "su -c getenforce": "Enforcing\n"}
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_harden_checks(adb, _facts(), root=True)
    ids = {f.check_id for f in report.findings}
    assert "sec.selinux" in ids


# ── Report rendering ──────────────────────────────────────────────────────────

def test_render_all_pass():
    adb = Adb(serial="S1", runner=_runner(_base_answers()))
    report = run_harden_checks(adb, _facts())
    text = render_harden_report(report)
    assert "Passing checks" in text
    assert "All checks passed." in text


def test_render_shows_failures():
    answers = _base_answers()
    answers["settings get secure lockscreen.disabled"] = "1\n"
    answers["settings get global adb_enabled"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_harden_checks(adb, _facts())
    text = render_harden_report(report)
    assert "✗" in text   # FAIL glyph
    assert "!" in text   # WARN glyph
    assert "issues need attention" in text


# ── Interactive mode ──────────────────────────────────────────────────────────

def test_interactive_no_confirm_shows_command(capsys):
    answers = _base_answers()
    answers["settings get global adb_enabled"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_harden_checks(adb, _facts())

    prompts: list[str] = []
    def prompter(msg: str) -> str:
        prompts.append(msg)
        return "y"

    run_interactive(report, adb, confirm=False, dry_run=False, prompter=prompter)
    captured = capsys.readouterr()
    assert "adb shell settings put global adb_enabled 0" in captured.out
    assert "re-run with --confirm" in captured.out


def test_interactive_dry_run_shows_would_run(capsys):
    answers = _base_answers()
    answers["settings get global adb_enabled"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_harden_checks(adb, _facts())

    run_interactive(report, adb, confirm=False, dry_run=True, prompter=lambda _: "y")
    captured = capsys.readouterr()
    assert "[dry-run]" in captured.out


def test_interactive_skips_when_n(capsys):
    answers = _base_answers()
    answers["settings get global adb_enabled"] = "1\n"
    adb = Adb(serial="S1", runner=_runner(answers))
    report = run_harden_checks(adb, _facts())

    run_interactive(report, adb, confirm=False, dry_run=False, prompter=lambda _: "n")
    captured = capsys.readouterr()
    # Should not print command if user said no
    assert "adb shell settings put global adb_enabled 0" not in captured.out


def test_interactive_applies_with_confirm(capsys):
    applied: list[str] = []

    answers = _base_answers()
    answers["settings get global adb_enabled"] = "1\n"
    answers["settings put global adb_enabled 0"] = ""

    def run(argv):
        cmd = argv[4]
        if cmd == "settings put global adb_enabled 0":
            applied.append(cmd)
            return AdbResult(0, "", "")
        return AdbResult(0, answers.get(cmd, ""), "")

    adb = Adb(serial="S1", runner=run)
    report = run_harden_checks(adb, _facts())
    run_interactive(report, adb, confirm=True, dry_run=False, prompter=lambda _: "y")

    assert "settings put global adb_enabled 0" in applied
    captured = capsys.readouterr()
    assert "Applied." in captured.out


def test_interactive_all_pass_prints_message(capsys):
    adb = Adb(serial="S1", runner=_runner(_base_answers()))
    report = run_harden_checks(adb, _facts())
    run_interactive(report, adb, confirm=False, dry_run=False, prompter=lambda _: "n")
    captured = capsys.readouterr()
    assert "all hardening checks passed" in captured.out.lower()
