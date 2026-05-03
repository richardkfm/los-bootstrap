"""Pre-flash checks: device state, manufacturer detection, ROM validation."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .models import DeviceState, Manufacturer, RomMetadata

if TYPE_CHECKING:
    from ..adb import Adb


_MANUFACTURER_MAP: dict[str, Manufacturer] = {
    "google": Manufacturer.GOOGLE,
    "oneplus": Manufacturer.ONEPLUS,
    "motorola": Manufacturer.MOTOROLA,
    "fairphone": Manufacturer.FAIRPHONE,
    "samsung": Manufacturer.SAMSUNG,
    "xiaomi": Manufacturer.XIAOMI,
    "redmi": Manufacturer.XIAOMI,   # Xiaomi sub-brand
    "poco": Manufacturer.XIAOMI,    # Xiaomi sub-brand
}


def detect_manufacturer(raw: str) -> Manufacturer:
    """Map a raw `ro.product.manufacturer` value to a Manufacturer enum."""
    return _MANUFACTURER_MAP.get(raw.strip().lower(), Manufacturer.GENERIC)


def detect_state(adb_stdout: str, fastboot_stdout: str) -> DeviceState:
    """Determine device state from `adb devices` + `fastboot devices` output."""
    for line in adb_stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            if parts[1] == "recovery":
                return DeviceState.RECOVERY
            if parts[1] == "device":
                return DeviceState.BOOTED
    for line in fastboot_stdout.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] == "fastboot":
            return DeviceState.FASTBOOT
    return DeviceState.UNKNOWN


def oem_unlock_enabled(adb: "Adb") -> bool:
    """Return True if OEM unlocking is toggled on in Developer Options."""
    try:
        return adb.setting_get("global", "oem_unlock_enabled") == "1"
    except Exception:
        return False


def developer_options_enabled(adb: "Adb") -> bool:
    """Return True if Developer Options are unlocked on the device."""
    try:
        return adb.setting_get("global", "development_settings_enabled") == "1"
    except Exception:
        return False


def is_ab_device(slot_count: str) -> bool:
    """Return True if the device uses an A/B partition layout.

    A/B devices report slot-count=2 via `fastboot getvar slot-count`.
    They have no dedicated recovery partition; ROM is applied via
    `fastboot update` or by flashing boot/system directly.
    """
    try:
        return int(slot_count) >= 2
    except (ValueError, TypeError):
        return False


def parse_rom_metadata(zip_path: Path) -> Optional[RomMetadata]:
    """Extract device target and build info from a LineageOS OTA zip.

    LineageOS zips contain META-INF/com/android/metadata with key=value
    pairs including `pre-device` (the target device codename).
    """
    candidates = [
        "META-INF/com/android/metadata",
        "META-INF/com/lineageos/metadata",
    ]
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for candidate in candidates:
                try:
                    data = zf.read(candidate).decode("utf-8", errors="replace")
                    meta = _parse_metadata_kv(data)
                    if meta:
                        return meta
                except KeyError:
                    continue
    except (zipfile.BadZipFile, OSError):
        return None
    return None


def _parse_metadata_kv(text: str) -> Optional[RomMetadata]:
    kv: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            kv[k.strip()] = v.strip()
    pre_device = kv.get("pre-device", "")
    if not pre_device:
        return None
    return RomMetadata(
        pre_device=pre_device,
        post_build=kv.get("post-build", ""),
        timestamp=kv.get("post-timestamp", ""),
    )
