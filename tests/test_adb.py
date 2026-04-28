"""Tests for the ADB wrapper. No real `adb` invoked."""

from __future__ import annotations

from los_bootstrap.adb import Adb, AdbResult, parse_devices


def make_runner(mapping: dict[tuple[str, ...], AdbResult]):
    def run(argv):
        key = tuple(argv)
        if key not in mapping:
            raise AssertionError(f"unexpected argv: {argv}")
        return mapping[key]

    return run


def test_parse_devices_skips_header_and_blanks():
    out = (
        "List of devices attached\n"
        "ABC123\tdevice\n"
        "\n"
        "DEF456\tunauthorized\n"
    )
    devs = parse_devices(out)
    assert [(d.serial, d.state) for d in devs] == [
        ("ABC123", "device"),
        ("DEF456", "unauthorized"),
    ]
    assert devs[0].ready
    assert not devs[1].ready


def test_package_installed_true_and_false():
    runner = make_runner(
        {
            ("adb", "-s", "S1", "shell", "pm list packages com.google.android.gms"): AdbResult(
                0, "package:com.google.android.gms\n", ""
            ),
            ("adb", "-s", "S1", "shell", "pm list packages com.example.absent"): AdbResult(
                0, "", ""
            ),
        }
    )
    adb = Adb(serial="S1", runner=runner)
    assert adb.package_installed("com.google.android.gms") is True
    assert adb.package_installed("com.example.absent") is False


def test_getprop_strips():
    runner = make_runner(
        {("adb", "shell", "getprop ro.product.device"): AdbResult(0, "lynx\n", "")}
    )
    adb = Adb(runner=runner)
    assert adb.getprop("ro.product.device") == "lynx"
