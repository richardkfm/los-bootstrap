"""Data models for GCam port camera profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class XmlConfig:
    """LMC / GCam XML configuration file descriptor."""

    filename: str
    device_path: str    # path on device where LMC/GCam expects the file
    description: str    # what this config tunes / which port uses it
    apply_hint: str     # exact adb command to push the file


@dataclass(frozen=True)
class CameraPort:
    """A single GCam port entry for a specific device."""

    name: str               # human name, e.g. "LMC 8.4 R17"
    package: str            # Android package name
    source_hint: str        # narrative text: where to obtain the APK
    verified: bool          # confirmed working on this device + LineageOS
    notes: str              # quirks, known issues, or tips
    xml_configs: Tuple[XmlConfig, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CameraProfile:
    """Per-device collection of known-working GCam port entries."""

    codename: str           # ro.product.device, e.g. "panther"
    display_name: str       # e.g. "Google Pixel 7"
    ports: Tuple[CameraPort, ...]
    notes: str = ""         # device-level notes (ROM quirks, etc.)
