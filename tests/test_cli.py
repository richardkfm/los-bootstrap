"""Tests for CLI parsing, exit codes, and device resolution."""

from __future__ import annotations

import pytest

from los_bootstrap.adb import AdbDevice
from los_bootstrap.cli import (
    EXIT_FINDINGS,
    EXIT_OK,
    EXIT_USAGE,
    _build_parser,
    _require_one_device,
)


def test_serial_accepted_before_and_after_subcommand():
    parser = _build_parser()
    assert parser.parse_args(["-s", "A", "audit"]).serial == "A"
    assert parser.parse_args(["audit", "-s", "B"]).serial == "B"
    assert parser.parse_args(["flash", "status", "--serial", "C"]).serial == "C"
    assert parser.parse_args(["location", "doctor", "-s", "D"]).serial == "D"


def test_subcommand_serial_wins_over_global():
    parser = _build_parser()
    args = parser.parse_args(["-s", "GLOBAL", "audit", "-s", "LOCAL"])
    assert args.serial == "LOCAL"


def test_no_banner_after_subcommand():
    parser = _build_parser()
    args = parser.parse_args(["report", "--no-banner", "--json"])
    assert args.no_banner and args.json


def test_version_flag_exits_zero(capsys):
    parser = _build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])
    assert exc.value.code == 0
    assert "los-bootstrap" in capsys.readouterr().out


def test_exit_code_constants_are_distinct():
    assert len({EXIT_OK, 1, EXIT_USAGE, EXIT_FINDINGS}) == 4


def test_require_one_device_unknown_serial_fails_clearly():
    devices = [AdbDevice("AAA", "device"), AdbDevice("BBB", "unauthorized")]
    with pytest.raises(SystemExit) as exc:
        _require_one_device(devices, "NOPE")
    assert "NOPE" in str(exc.value)
    assert "AAA" in str(exc.value)


def test_require_one_device_unauthorized_serial_fails_clearly():
    devices = [AdbDevice("BBB", "unauthorized")]
    with pytest.raises(SystemExit) as exc:
        _require_one_device(devices, "BBB")
    assert "unauthorized" in str(exc.value)


def test_require_one_device_valid_serial_ok():
    devices = [AdbDevice("AAA", "device"), AdbDevice("BBB", "device")]
    assert _require_one_device(devices, "AAA") == "AAA"


def test_flash_context_detects_samsung_download_mode(monkeypatch):
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.adb import AdbResult
    from los_bootstrap.flash.models import DeviceState

    monkeypatch.setattr(cli_mod.Adb, "raw", lambda self, *a: AdbResult(0, "", ""))
    monkeypatch.setattr(
        cli_mod.Fastboot, "raw",
        lambda self, *a: __import__("los_bootstrap.flash.fastboot", fromlist=["FastbootResult"]).FastbootResult(0, "", ""),
    )
    monkeypatch.setattr(cli_mod, "heimdall_available", lambda: True)
    monkeypatch.setattr(cli_mod.Heimdall, "detect", lambda self: True)

    ctx = cli_mod._detect_flash_context(None)
    assert ctx.state == DeviceState.DOWNLOAD
