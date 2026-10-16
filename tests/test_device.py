"""Tests for device.py — form_factor and /e/OS detection."""

from __future__ import annotations

import pytest

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.device import collect, parse_eos_version, rom_label


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


# ---------------------------------------------------------------------------
# /e/OS detection — /e/OS writes its own release into ro.lineage.version
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("4.3-a14-20260921678710-community-bluejay", ("4.3", "community")),
        ("3.4-a16-20251017537822-official-FP5", ("3.4", "official")),
        ("2.0-t-20240514401520-stable-FP4", ("2.0", "stable")),
        ("3.0.1-beta.1-u-20250101-dev-FP4", ("3.0.1", "dev")),
        ("2.0-t-20240514_101010-UNOFFICIAL-mybuild-FP4", ("2.0", "unofficial")),
    ],
)
def test_parse_eos_version_recognises_eos(raw, expected):
    assert parse_eos_version(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["21.0-20240101-NIGHTLY-panther", "22.1-20250101-microG-panther", "21.0", "", None],
)
def test_parse_eos_version_rejects_lineageos(raw):
    assert parse_eos_version(raw) is None


def test_eos_device_is_not_reported_as_lineageos():
    props = _base_props(**{"ro.lineage.version": "4.3-a14-20260921678710-community-bluejay"})
    facts = collect(Adb(serial="S1", runner=_runner(props)))
    assert facts.is_eos
    assert not facts.is_lineage
    assert facts.eos_version == "4.3"
    assert facts.eos_channel == "community"
    assert rom_label(facts) == "/e/OS 4.3 (LineageOS-based, community)"


def test_lineageos_device_is_not_eos():
    facts = collect(Adb(serial="S1", runner=_runner(_base_props())))
    assert facts.is_lineage
    assert not facts.is_eos
    assert rom_label(facts) == "LineageOS 21.0"
