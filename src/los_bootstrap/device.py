"""Device facts derived from `getprop`.

Pure data: this module reads, it does not interpret. Interpretation
(audit findings, recommendations) lives in `audit/` and `bootstrap.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .adb import Adb


@dataclass(frozen=True)
class DeviceFacts:
    serial: str
    manufacturer: str
    model: str
    codename: str  # ro.product.device, e.g. "lynx"
    android_release: str  # e.g. "14"
    sdk: str  # e.g. "34"
    security_patch: str  # e.g. "2025-12-01"
    build_id: str
    build_fingerprint: str
    is_lineage: bool  # upstream LineageOS; False on /e/OS, which reuses the property
    lineage_version: Optional[str]  # raw ro.lineage.version
    adb_tcp_port: Optional[str]  # service.adb.tcp.port (or None / "")
    form_factor: str  # "tablet" or "phone" — derived from ro.build.characteristics
    build_date_utc: Optional[int] = None  # ro.build.date.utc (epoch seconds); None when unset
    eos_version: Optional[str] = None  # /e/OS release, e.g. "4.3"; None when not /e/OS
    eos_channel: Optional[str] = None  # /e/OS build type, e.g. "official", "community"

    @property
    def is_eos(self) -> bool:
        return self.eos_version is not None


# /e/OS builds on LineageOS's vendor tree and writes its own release into
# ro.lineage.version: "<e version>[-<prerelease>]-<android>-<date><ci id>-<type>-<device>",
# e.g. "4.3-a14-20260921678710-community-bluejay" or "1.0-r-20220526-stable-FP3".
# Upstream LineageOS has the date right after the version
# ("21.0-20240101-NIGHTLY-panther"), so the Android segment tells them apart.
_EOS_VERSION_RE = re.compile(
    r"^(?P<version>\d+\.\d+(?:\.\d+)?)"
    r"(?:-[A-Za-z]+(?:\.\d+)?)?"
    r"-(?:a\d{2}|[a-z])"
    r"-\d{8}[0-9_]*"
    r"-(?P<channel>[A-Za-z]+)(?:-|$)"
)


def parse_eos_version(lineage_version: Optional[str]) -> Optional[tuple[str, str]]:
    """Return (/e/OS version, build type) if ``ro.lineage.version`` is /e/OS."""
    match = _EOS_VERSION_RE.match((lineage_version or "").strip())
    if match is None:
        return None
    return match.group("version"), match.group("channel").lower()


def rom_label(facts: DeviceFacts) -> str:
    """Human-readable ROM name for device summaries."""
    if facts.is_eos:
        channel = f", {facts.eos_channel}" if facts.eos_channel else ""
        return f"/e/OS {facts.eos_version} (LineageOS-based{channel})"
    if facts.is_lineage:
        return f"LineageOS {facts.lineage_version or ''}".rstrip()
    return "AOSP-derived"


def collect(adb: Adb) -> DeviceFacts:
    """Read device identity properties via getprop."""
    g = adb.getprop
    lineage_version = g("ro.lineage.version") or None
    adb_tcp_port = g("service.adb.tcp.port") or None
    characteristics = g("ro.build.characteristics") or ""
    form_factor = "tablet" if "tablet" in characteristics.lower() else "phone"
    build_date_utc = _parse_build_date_utc(g("ro.build.date.utc"))
    eos = parse_eos_version(lineage_version)
    return DeviceFacts(
        serial=adb.serial or "",
        manufacturer=g("ro.product.manufacturer"),
        model=g("ro.product.model"),
        codename=g("ro.product.device"),
        android_release=g("ro.build.version.release"),
        sdk=g("ro.build.version.sdk"),
        security_patch=g("ro.build.version.security_patch"),
        build_id=g("ro.build.id"),
        build_fingerprint=g("ro.build.fingerprint"),
        is_lineage=bool(lineage_version) and eos is None,
        lineage_version=lineage_version,
        adb_tcp_port=adb_tcp_port,
        form_factor=form_factor,
        build_date_utc=build_date_utc,
        eos_version=eos[0] if eos else None,
        eos_channel=eos[1] if eos else None,
    )


def _parse_build_date_utc(raw: str) -> Optional[int]:
    """Parse `ro.build.date.utc` (epoch seconds) into an int, or None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
