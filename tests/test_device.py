"""Tests for device.py — form_factor detection."""

from __future__ import annotations

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.device import collect


def _runner(props: dict[str, str]):
    """Build a runner that satisfies adb.shell('getprop <key>') lookups."""
    def run(argv):
        # argv: ["adb", "-s", serial, "shell", "getprop <key>"]
        cmd = argv[4]  # e.g. "getprop ro.build.characteristics"
        if cmd.startswith("getprop "):
            key = cmd[len("getprop "):]
            return AdbResult(0, props.get(key, ""), "")
        return AdbResult(0, "", "")
    return run


def _base_props(**overrides) -> dict[str, str]:
    base = {
        "ro.product.manufacturer": "Google",
        "ro.product.model": "Pixel 7",
        "ro.product.device": "panther",
        "ro.build.version.release": "14",
        "ro.build.version.sdk": "34",
        "ro.build.version.security_patch": "2025-12-01",
        "ro.build.id": "UQ1A.000000.000",
        "ro.build.fingerprint": "fp",
        "ro.lineage.version": "21.0",
        "service.adb.tcp.port": "",
        "ro.build.characteristics": "default",
    }
    base.update(overrides)
    return base


def test_phone_form_factor_from_default_characteristics():
    adb = Adb(serial="S1", runner=_runner(_base_props()))
    facts = collect(adb)
    assert facts.form_factor == "phone"


def test_phone_form_factor_when_characteristics_empty():
    adb = Adb(serial="S1", runner=_runner(_base_props(**{"ro.build.characteristics": ""})))
    facts = collect(adb)
    assert facts.form_factor == "phone"


def test_tablet_form_factor_detected():
    adb = Adb(serial="S1", runner=_runner(_base_props(**{"ro.build.characteristics": "tablet"})))
    facts = collect(adb)
    assert facts.form_factor == "tablet"


def test_tablet_form_factor_detected_with_extra_flags():
    # Some ROMs set "tablet,nosdcard" or similar compound values.
    adb = Adb(serial="S1", runner=_runner(_base_props(**{"ro.build.characteristics": "tablet,nosdcard"})))
    facts = collect(adb)
    assert facts.form_factor == "tablet"
