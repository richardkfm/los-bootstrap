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


# ---------------------------------------------------------------------------
# Phase 11 flash lifecycle — end-to-end command behavior and exit codes
# ---------------------------------------------------------------------------

_LIFECYCLE_PROPS = {
    "ro.product.manufacturer": "Google",
    "ro.product.model": "Pixel 7",
    "ro.product.device": "panther",
    "ro.build.version.release": "15",
    "ro.build.version.sdk": "35",
    "ro.build.version.security_patch": "2025-12-01",
    "ro.build.id": "AP2A.250705.003",
    "ro.build.fingerprint": (
        "google/lineage_panther/panther:15/AP2A.250705.003/1234567:userdebug/test-keys"
    ),
    "ro.lineage.version": "21.0",
    "ro.build.characteristics": "phone",
    "ro.build.date.utc": "1700000000",
    "ro.boot.verifiedbootstate": "orange",
    "ro.build.type": "userdebug",
    "ro.boot.slot_suffix": "_b",
}


class _StubAdb:
    """Stands in for a booted, degoogled LineageOS device."""

    def __init__(self, props=None, serial=None, gms_version=None):
        self._props = dict(props if props is not None else _LIFECYCLE_PROPS)
        self.serial = serial
        self._gms_version = gms_version

    def getprop(self, key: str) -> str:
        return self._props.get(key, "")

    def package_installed(self, package: str) -> bool:
        return self._gms_version is not None

    def shell(self, command: str) -> str:
        return f"    versionName={self._gms_version}\n"


def _stub_booted_device(monkeypatch, adb=None, **ctx_overrides):
    """Make _detect_flash_context report a booted device backed by `adb`."""
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.flash.models import DeviceState, Manufacturer

    target = adb if adb is not None else _StubAdb()
    ctx = cli_mod._FlashContext(
        state=ctx_overrides.get("state", DeviceState.BOOTED),
        manufacturer=Manufacturer.GOOGLE,
        codename="panther",
        dev_opts=True,
        oem_unlock=True,
        target_adb=None if ctx_overrides.get("no_target") else target,
        fb=cli_mod.Fastboot(),
    )
    monkeypatch.setattr(cli_mod, "_detect_flash_context", lambda serial: ctx)
    return target


def _lineage_build(datetime_epoch: int, version: str = "21.0"):
    from los_bootstrap.flash.distros import LineageBuild

    return LineageBuild(
        codename="panther",
        filename=f"lineage-{version}-panther.zip",
        url=f"https://example.invalid/lineage-{version}-panther.zip",
        size=1024,
        sha256="deadbeef",
        version=version,
        datetime=datetime_epoch,
        build_type="nightly",
    )


def test_flash_backup_needs_no_device(capsys):
    from los_bootstrap.cli import main

    assert main(["flash", "backup", "--no-banner"]) == EXIT_OK
    assert "Pre-flash backup guidance" in capsys.readouterr().out


def test_flash_check_clean_device_exits_zero(monkeypatch, capsys):
    from los_bootstrap.cli import main

    _stub_booted_device(monkeypatch)
    assert main(["flash", "check", "--no-banner"]) == EXIT_OK
    assert "Clean first boot" in capsys.readouterr().out


def test_flash_check_reports_findings_exit_code(monkeypatch, capsys):
    from los_bootstrap.cli import main

    props = dict(_LIFECYCLE_PROPS, **{"ro.boot.verifiedbootstate": "red"})
    _stub_booted_device(monkeypatch, _StubAdb(props))
    assert main(["flash", "check", "--no-banner"]) == EXIT_FINDINGS
    assert "Verified Boot reported a failure" in capsys.readouterr().out


def test_flash_check_microg_device_is_not_a_finding(monkeypatch, capsys):
    """LineageOS for microG is a supported target — it must not exit 3."""
    from los_bootstrap.cli import main

    _stub_booted_device(monkeypatch, _StubAdb(gms_version="0.3.6.244735"))
    assert main(["flash", "check", "--no-banner"]) == EXIT_OK
    assert "microG" in capsys.readouterr().out


def test_flash_check_without_device_is_a_usage_error(monkeypatch, capsys):
    from los_bootstrap.cli import main

    _stub_booted_device(monkeypatch, no_target=True)
    assert main(["flash", "check", "--no-banner"]) == EXIT_USAGE
    assert "needs a booted ADB device" in capsys.readouterr().err


def test_flash_update_up_to_date_exits_zero(monkeypatch, capsys):
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.cli import main

    _stub_booted_device(monkeypatch)
    monkeypatch.setattr(
        cli_mod, "lookup_lineage_builds", lambda codename: [_lineage_build(1700000000)]
    )
    assert main(["flash", "update", "--no-banner"]) == EXIT_OK
    assert "up to date" in capsys.readouterr().out


def test_flash_update_outdated_exits_three(monkeypatch, capsys):
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.cli import main

    _stub_booted_device(monkeypatch)
    monkeypatch.setattr(
        cli_mod,
        "lookup_lineage_builds",
        lambda codename: [_lineage_build(1700000000 + 5 * 86400)],
    )
    assert main(["flash", "update", "--no-banner"]) == EXIT_FINDINGS
    assert "5 days behind" in capsys.readouterr().out


def test_flash_update_no_network_skips_lookup(monkeypatch, capsys):
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.cli import main

    _stub_booted_device(monkeypatch)

    def _boom(codename):
        raise AssertionError("--no-network must not query the API")

    monkeypatch.setattr(cli_mod, "lookup_lineage_builds", _boom)
    assert main(["flash", "update", "--no-network", "--no-banner"]) == EXIT_OK
    assert "--no-network" in capsys.readouterr().out


def test_flash_update_no_network_still_reports_non_lineage(monkeypatch, capsys):
    """This verdict needs no API call, so --no-network must not hide it."""
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.cli import main

    props = dict(_LIFECYCLE_PROPS)
    props["ro.lineage.version"] = ""
    _stub_booted_device(monkeypatch, _StubAdb(props))
    monkeypatch.setattr(cli_mod, "lookup_lineage_builds", lambda codename: [])
    assert main(["flash", "update", "--no-network", "--no-banner"]) == EXIT_OK
    assert "not running LineageOS" in capsys.readouterr().out


def test_flash_update_api_failure_still_renders_a_report(monkeypatch, capsys):
    """Mirrors `flash download`: an unreachable API degrades, it does not abort."""
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.cli import main
    from los_bootstrap.flash import DistroFetchError

    _stub_booted_device(monkeypatch)

    def _fail(codename):
        raise DistroFetchError("network error querying LineageOS API")

    monkeypatch.setattr(cli_mod, "lookup_lineage_builds", _fail)
    assert main(["flash", "update", "--no-banner"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "LineageOS API unavailable" in out
    assert "download.lineageos.org/devices/panther" in out


def test_flash_update_empty_codename_is_a_usage_error(monkeypatch, capsys):
    from los_bootstrap.cli import main

    props = dict(_LIFECYCLE_PROPS)
    props["ro.product.device"] = ""
    _stub_booted_device(monkeypatch, _StubAdb(props))
    assert main(["flash", "update", "--no-banner"]) == EXIT_USAGE
    assert "codename" in capsys.readouterr().err


def test_flash_update_flags_major_upgrade(monkeypatch, capsys):
    from los_bootstrap import cli as cli_mod
    from los_bootstrap.cli import main

    _stub_booted_device(monkeypatch)
    monkeypatch.setattr(
        cli_mod,
        "lookup_lineage_builds",
        lambda codename: [
            _lineage_build(1700000000 + 40 * 86400, version="22.0"),
            _lineage_build(1700000000, version="21.0"),
        ],
    )
    assert main(["flash", "update", "--no-banner"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "up to date" in out
    assert "newer major version" in out
    assert "full data wipe" in out
