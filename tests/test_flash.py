"""Tests for the flash/ package (Phase 8).

No real ADB or fastboot connection is needed — all IO is injected.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from los_bootstrap.flash.checks import (
    detect_manufacturer,
    detect_state,
    is_ab_device,
    parse_rom_metadata,
    _parse_metadata_kv,
)
from los_bootstrap.flash.fastboot import Fastboot, FastbootNotFoundError, FastbootResult
from los_bootstrap.flash.heimdall import Heimdall, HeimdallNotFoundError, HeimdallResult
from los_bootstrap.flash.models import DeviceState, FlashStepKind, Manufacturer
from los_bootstrap.flash.plan import build_flash_plan
from los_bootstrap.flash.report import (
    render_flash_plan,
    render_flash_status,
    render_verify_result,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fastboot_runner(mapping: dict) -> object:
    def runner(argv):
        key = tuple(argv)
        if key in mapping:
            return mapping[key]
        return FastbootResult(0, "", "")
    return runner


def make_heimdall_runner(mapping: dict) -> object:
    def runner(argv):
        key = tuple(argv)
        if key in mapping:
            return mapping[key]
        return HeimdallResult(0, "", "")
    return runner


# ---------------------------------------------------------------------------
# detect_manufacturer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Google", Manufacturer.GOOGLE),
    ("google", Manufacturer.GOOGLE),
    ("OnePlus", Manufacturer.ONEPLUS),
    ("ONEPLUS", Manufacturer.ONEPLUS),
    ("motorola", Manufacturer.MOTOROLA),
    ("Motorola", Manufacturer.MOTOROLA),
    ("Fairphone", Manufacturer.FAIRPHONE),
    ("samsung", Manufacturer.SAMSUNG),
    ("Samsung", Manufacturer.SAMSUNG),
    ("Xiaomi", Manufacturer.XIAOMI),
    ("xiaomi", Manufacturer.XIAOMI),
    ("Redmi", Manufacturer.XIAOMI),
    ("POCO", Manufacturer.XIAOMI),
    ("unknown_oem", Manufacturer.GENERIC),
    ("", Manufacturer.GENERIC),
])
def test_detect_manufacturer(raw, expected):
    assert detect_manufacturer(raw) == expected


# ---------------------------------------------------------------------------
# detect_state
# ---------------------------------------------------------------------------

def test_detect_state_booted():
    adb_out = "List of devices attached\nABCD1234\tdevice\n"
    fb_out = ""
    assert detect_state(adb_out, fb_out) == DeviceState.BOOTED


def test_detect_state_recovery():
    adb_out = "List of devices attached\nABCD1234\trecovery\n"
    fb_out = ""
    assert detect_state(adb_out, fb_out) == DeviceState.RECOVERY


def test_detect_state_fastboot():
    adb_out = "List of devices attached\n"
    fb_out = "ABCD1234\tfastboot\n"
    assert detect_state(adb_out, fb_out) == DeviceState.FASTBOOT


def test_detect_state_unknown():
    assert detect_state("", "") == DeviceState.UNKNOWN


def test_detect_state_prefers_adb_over_fastboot():
    adb_out = "List of devices attached\nABCD1234\tdevice\n"
    fb_out = "ABCD1234\tfastboot\n"
    assert detect_state(adb_out, fb_out) == DeviceState.BOOTED


# ---------------------------------------------------------------------------
# is_ab_device
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("slot_count,expected", [
    ("2", True),
    ("4", True),
    ("1", False),
    ("0", False),
    ("", False),
    ("not-a-number", False),
])
def test_is_ab_device(slot_count, expected):
    assert is_ab_device(slot_count) == expected


# ---------------------------------------------------------------------------
# parse_rom_metadata — in-memory zip
# ---------------------------------------------------------------------------

def _make_metadata_zip(metadata_text: str, entry: str = "META-INF/com/android/metadata") -> Path:
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(entry, metadata_text)
    return Path(path)


def test_parse_rom_metadata_success(tmp_path):
    metadata = (
        "pre-device=panther\n"
        "post-build=lineage_panther-user 13 TQ3A 20231215 release-keys\n"
        "post-timestamp=1702627200\n"
    )
    zip_path = tmp_path / "rom.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("META-INF/com/android/metadata", metadata)

    result = parse_rom_metadata(zip_path)
    assert result is not None
    assert result.pre_device == "panther"
    assert "lineage_panther" in result.post_build
    assert result.timestamp == "1702627200"


def test_parse_rom_metadata_lineageos_path(tmp_path):
    metadata = "pre-device=oriole\npost-build=lineage_oriole-user 13\n"
    zip_path = tmp_path / "rom.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("META-INF/com/lineageos/metadata", metadata)

    result = parse_rom_metadata(zip_path)
    assert result is not None
    assert result.pre_device == "oriole"


def test_parse_rom_metadata_no_pre_device(tmp_path):
    metadata = "post-build=something\npost-timestamp=123\n"
    zip_path = tmp_path / "rom.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("META-INF/com/android/metadata", metadata)

    assert parse_rom_metadata(zip_path) is None


def test_parse_rom_metadata_bad_zip(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip file")
    assert parse_rom_metadata(bad) is None


def test_parse_rom_metadata_missing_file(tmp_path):
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w"):
        pass
    assert parse_rom_metadata(zip_path) is None


# ---------------------------------------------------------------------------
# Fastboot wrapper
# ---------------------------------------------------------------------------

def test_fastboot_devices():
    runner = make_fastboot_runner({
        ("fastboot", "devices"): FastbootResult(0, "SERIAL1\tfastboot\n", ""),
    })
    fb = Fastboot(runner=runner)
    assert fb.devices() == ["SERIAL1"]


def test_fastboot_devices_empty():
    runner = make_fastboot_runner({
        ("fastboot", "devices"): FastbootResult(0, "", ""),
    })
    fb = Fastboot(runner=runner)
    assert fb.devices() == []


def test_fastboot_getvar():
    runner = make_fastboot_runner({
        ("fastboot", "getvar", "unlocked"): FastbootResult(0, "", "unlocked: yes\nFINISHED\n"),
    })
    fb = Fastboot(runner=runner)
    assert fb.getvar("unlocked") == "yes"


def test_fastboot_getvar_product():
    runner = make_fastboot_runner({
        ("fastboot", "getvar", "product"): FastbootResult(0, "", "product: panther\nFINISHED\n"),
    })
    fb = Fastboot(runner=runner)
    assert fb.getvar("product") == "panther"


def test_fastboot_getvar_missing_key():
    runner = make_fastboot_runner({
        ("fastboot", "getvar", "slot-count"): FastbootResult(0, "", "FINISHED\n"),
    })
    fb = Fastboot(runner=runner)
    assert fb.getvar("slot-count") == ""


def test_fastboot_with_serial():
    runner = make_fastboot_runner({
        ("fastboot", "-s", "SER1", "getvar", "unlocked"): FastbootResult(0, "", "unlocked: no\n"),
    })
    fb = Fastboot(serial="SER1", runner=runner)
    assert fb.getvar("unlocked") == "no"


def test_fastboot_not_found():
    def failing_runner(argv):
        raise FastbootNotFoundError("`fastboot` not found on PATH")
    fb = Fastboot(runner=failing_runner)
    with pytest.raises(FastbootNotFoundError):
        fb.raw("devices")


# ---------------------------------------------------------------------------
# Heimdall wrapper
# ---------------------------------------------------------------------------

def test_heimdall_detect_success():
    runner = make_heimdall_runner({
        ("heimdall", "detect"): HeimdallResult(0, "Device detected", ""),
    })
    h = Heimdall(runner=runner)
    assert h.detect() is True


def test_heimdall_detect_failure():
    runner = make_heimdall_runner({
        ("heimdall", "detect"): HeimdallResult(1, "", "ERROR: Failed to detect device"),
    })
    h = Heimdall(runner=runner)
    assert h.detect() is False


def test_heimdall_flash_success():
    runner = make_heimdall_runner({
        ("heimdall", "flash", "--RECOVERY", "/tmp/recovery.img"):
            HeimdallResult(0, "Session ended successfully.", ""),
    })
    h = Heimdall(runner=runner)
    result = h.flash("RECOVERY", "/tmp/recovery.img")
    assert result.returncode == 0


def test_heimdall_flash_failure():
    from los_bootstrap.flash.heimdall import HeimdallCommandError
    runner = make_heimdall_runner({
        ("heimdall", "flash", "--RECOVERY", "/tmp/recovery.img"):
            HeimdallResult(1, "", "ERROR: Protocol initialisation failed!"),
    })
    h = Heimdall(runner=runner)
    with pytest.raises(HeimdallCommandError):
        h.flash("RECOVERY", "/tmp/recovery.img")


# ---------------------------------------------------------------------------
# build_flash_plan
# ---------------------------------------------------------------------------

def test_build_flash_plan_aonly(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()
    recovery = tmp_path / "recovery.img"
    recovery.touch()

    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
        recovery_path=recovery,
        ab_device=False,
    )

    kinds = [s.kind for s in plan.steps]
    assert FlashStepKind.ADB_REBOOT in kinds
    assert FlashStepKind.FASTBOOT_FLASH in kinds
    assert FlashStepKind.FASTBOOT_REBOOT in kinds
    assert FlashStepKind.ADB_SIDELOAD in kinds


def test_build_flash_plan_ab(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()

    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
        ab_device=True,
    )

    kinds = [s.kind for s in plan.steps]
    assert FlashStepKind.ADB_REBOOT in kinds
    assert FlashStepKind.FASTBOOT_UPDATE in kinds
    assert FlashStepKind.FASTBOOT_FLASH not in kinds


def test_build_flash_plan_samsung_heimdall(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()
    recovery = tmp_path / "recovery.img"
    recovery.touch()

    plan = build_flash_plan(
        manufacturer=Manufacturer.SAMSUNG,
        device_codename="dreamlte",
        rom_path=rom,
        recovery_path=recovery,
        heimdall_available=True,
    )

    kinds = [s.kind for s in plan.steps]
    assert FlashStepKind.HEIMDALL_FLASH in kinds
    assert FlashStepKind.ADB_SIDELOAD in kinds
    # At least two MANUAL steps (enter download mode, boot recovery immediately)
    assert kinds.count(FlashStepKind.MANUAL) >= 2


def test_build_flash_plan_samsung_no_heimdall(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()

    plan = build_flash_plan(
        manufacturer=Manufacturer.SAMSUNG,
        device_codename="dreamlte",
        rom_path=rom,
        heimdall_available=False,
    )

    kinds = [s.kind for s in plan.steps]
    assert FlashStepKind.MANUAL in kinds
    assert FlashStepKind.HEIMDALL_FLASH not in kinds
    assert FlashStepKind.ADB_SIDELOAD in kinds


def test_build_flash_plan_xiaomi(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()

    plan = build_flash_plan(
        manufacturer=Manufacturer.XIAOMI,
        device_codename="sunny",
        rom_path=rom,
        ab_device=False,
    )

    kinds = [s.kind for s in plan.steps]
    assert FlashStepKind.MANUAL in kinds      # Mi Unlock reminder
    assert FlashStepKind.ADB_SIDELOAD in kinds


# ---------------------------------------------------------------------------
# Renderers — smoke tests (just check they return non-empty strings)
# ---------------------------------------------------------------------------

def test_render_flash_status_booted():
    text = render_flash_status(
        DeviceState.BOOTED,
        Manufacturer.GOOGLE,
        "panther",
        bootloader_unlocked=False,
        dev_options=True,
        oem_unlocking=True,
    )
    assert "booted" in text.lower()
    assert "Google" in text
    assert "panther" in text


def test_render_flash_status_unknown():
    text = render_flash_status(DeviceState.UNKNOWN, None, "")
    assert "unknown" in text.lower()


def test_render_flash_plan_smoke(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()
    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
    )
    text = render_flash_plan(plan)
    assert "panther" in text
    assert "Google" in text


def test_render_verify_result_match(tmp_path):
    from los_bootstrap.flash.models import RomMetadata
    rom = tmp_path / "lineage.zip"
    rom.touch()
    meta = RomMetadata(pre_device="panther", post_build="lineage_panther", timestamp="123")
    text = render_verify_result(rom, True, meta, "panther")
    assert "MATCH" in text


def test_render_verify_result_mismatch(tmp_path):
    from los_bootstrap.flash.models import RomMetadata
    rom = tmp_path / "lineage.zip"
    rom.touch()
    meta = RomMetadata(pre_device="panther", post_build="lineage_panther", timestamp="123")
    text = render_verify_result(rom, True, meta, "oriole")
    assert "MISMATCH" in text


def test_render_verify_result_bad_zip(tmp_path):
    rom = tmp_path / "bad.zip"
    rom.touch()
    text = render_verify_result(rom, False, None, "")
    assert "INVALID" in text


def test_render_download_options_with_build():
    from los_bootstrap.flash.distros import LineageBuild
    from los_bootstrap.flash.report import render_download_options

    build = LineageBuild(
        codename="bluejay",
        filename="lineage-21.0-bluejay.zip",
        url="https://example.invalid/lineage-21.0-bluejay.zip",
        size=1500 * 1024 * 1024,
        sha256="deadbeef",
        version="21.0",
        datetime=200,
        build_type="nightly",
    )
    text = render_download_options(
        codename="bluejay",
        build=build,
        page_url="https://download.lineageos.org/devices/bluejay/builds",
        alt_links=[("DivestOS", "https://divestos.org/index.php?page=devices")],
    )
    assert "bluejay" in text
    assert "lineage-21.0-bluejay.zip" in text
    assert "deadbeef" in text
    assert "DivestOS" in text


def test_render_download_options_no_build_falls_back_to_page_url():
    from los_bootstrap.flash.report import render_download_options

    text = render_download_options(
        codename="rarephone",
        build=None,
        page_url="https://download.lineageos.org/devices/rarephone/builds",
        alt_links=[("/e/OS", "https://images.ecloud.global/stable/rarephone/")],
    )
    assert "No official LineageOS build" in text
    assert "rarephone" in text
    assert "/e/OS" in text


def test_render_download_options_api_error_surfaces_reason():
    from los_bootstrap.flash.report import render_download_options

    text = render_download_options(
        codename="bluejay",
        build=None,
        page_url="https://download.lineageos.org/devices/bluejay/builds",
        alt_links=[],
        api_error="connection refused",
    )
    assert "connection refused" in text


def test_fastboot_reboot_failure_raises():
    from los_bootstrap.flash.fastboot import FastbootCommandError
    runner = make_fastboot_runner({
        ("fastboot", "reboot", "recovery"):
            FastbootResult(1, "", "fastboot: usage: unknown reboot target recovery"),
    })
    fb = Fastboot(runner=runner)
    with pytest.raises(FastbootCommandError):
        fb.reboot("recovery")


def test_fastboot_oem_unlock_failure_raises():
    from los_bootstrap.flash.fastboot import FastbootCommandError
    runner = make_fastboot_runner({
        ("fastboot", "flashing", "unlock"):
            FastbootResult(1, "", "FAILED (remote: 'oem unlock is not allowed')"),
    })
    fb = Fastboot(runner=runner)
    with pytest.raises(FastbootCommandError):
        fb.oem_unlock()


def test_flash_steps_marked_destructive(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()
    recovery = tmp_path / "recovery.img"
    recovery.touch()

    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
        recovery_path=recovery,
        ab_device=False,
    )
    destructive_kinds = {
        s.kind for s in plan.steps if s.is_destructive
    }
    assert FlashStepKind.FASTBOOT_FLASH in destructive_kinds
    assert FlashStepKind.ADB_SIDELOAD in destructive_kinds


def test_ab_update_step_marked_destructive(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()
    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
        ab_device=True,
    )
    update = [s for s in plan.steps if s.kind == FlashStepKind.FASTBOOT_UPDATE]
    assert update and all(s.is_destructive for s in update)


def test_sideload_preceded_by_manual_sideload_mode_step(tmp_path):
    rom = tmp_path / "lineage.zip"
    rom.touch()
    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
        ab_device=False,
    )
    kinds = [s.kind for s in plan.steps]
    idx = kinds.index(FlashStepKind.ADB_SIDELOAD)
    assert kinds[idx - 1] == FlashStepKind.MANUAL
    assert "sideload" in plan.steps[idx - 1].description.lower()


def test_execute_flash_plan_pauses_on_manual_steps(tmp_path, capsys):
    from los_bootstrap.adb import Adb, AdbResult
    from los_bootstrap.flash.flash import execute_flash_plan

    rom = tmp_path / "lineage.zip"
    rom.touch()
    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
        ab_device=False,
    )

    pauses: list[str] = []
    adb = Adb(runner=lambda argv: AdbResult(0, "", ""))
    fb = Fastboot(runner=make_fastboot_runner({}))
    result = execute_flash_plan(
        plan,
        adb=adb,
        fastboot=fb,
        confirm=True,
        dry_run=False,
        pause=lambda msg: pauses.append(msg),
    )
    manual_count = sum(1 for s in plan.steps if s.kind == FlashStepKind.MANUAL)
    assert len(pauses) == manual_count
    assert not result.had_errors()


def test_execute_flash_plan_skips_destructive_without_confirm(tmp_path):
    from los_bootstrap.adb import Adb, AdbResult
    from los_bootstrap.flash.flash import execute_flash_plan

    rom = tmp_path / "lineage.zip"
    rom.touch()
    plan = build_flash_plan(
        manufacturer=Manufacturer.GOOGLE,
        device_codename="panther",
        rom_path=rom,
        ab_device=True,
    )

    executed: list[list[str]] = []

    def recording_runner(argv):
        executed.append(list(argv))
        return FastbootResult(0, "", "")

    adb_calls: list[list[str]] = []

    def adb_runner(argv):
        adb_calls.append(list(argv))
        return AdbResult(0, "", "")

    adb = Adb(runner=adb_runner)
    fb = Fastboot(runner=recording_runner)
    result = execute_flash_plan(
        plan, adb=adb, fastboot=fb, confirm=False, dry_run=False,
        pause=lambda msg: None,
    )
    # `fastboot update` is destructive and must not run without confirm
    assert not any(argv[1] == "update" for argv in executed)
    assert result.steps_skipped >= 1


def test_render_download_options_can_hide_fetch_hint():
    from los_bootstrap.flash.distros import LineageBuild
    from los_bootstrap.flash.report import render_download_options

    build = LineageBuild(
        codename="bluejay", filename="l.zip", url="https://example.invalid/l.zip",
        size=1, sha256="", version="21.0", datetime=1, build_type="nightly",
    )
    shown = render_download_options(
        codename="bluejay", build=build, page_url="p", alt_links=[],
    )
    hidden = render_download_options(
        codename="bluejay", build=build, page_url="p", alt_links=[],
        show_fetch_hint=False,
    )
    assert "--fetch" in shown
    assert "--fetch" not in hidden
