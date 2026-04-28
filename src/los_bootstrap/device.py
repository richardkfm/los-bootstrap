"""Device facts derived from `getprop`.

Pure data: this module reads, it does not interpret. Interpretation
(audit findings, recommendations) lives in `audit/` and `bootstrap.py`.
"""

from __future__ import annotations

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
    is_lineage: bool
    lineage_version: Optional[str]
    adb_tcp_port: Optional[str]  # service.adb.tcp.port (or None / "")


def collect(adb: Adb) -> DeviceFacts:
    """Read device identity properties via getprop."""
    g = adb.getprop
    lineage_version = g("ro.lineage.version") or None
    adb_tcp_port = g("service.adb.tcp.port") or None
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
        is_lineage=bool(lineage_version),
        lineage_version=lineage_version,
        adb_tcp_port=adb_tcp_port,
    )
