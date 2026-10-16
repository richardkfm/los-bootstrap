"""Shared classification of the com.google.android.gms package.

microG GmsCore installs under the real Play Services package id — that is
the whole point of microG — so presence alone cannot distinguish the two.
`audit/`, `location/`, `flash/` and `integrity/` all need that distinction,
so the heuristic lives here rather than being duplicated.

Read-only. No state is mutated.
"""

from __future__ import annotations

from .adb import Adb, AdbCommandError

GMS_PACKAGE = "com.google.android.gms"
GSF_PACKAGE = "com.google.android.gsf"
VENDING_PACKAGE = "com.android.vending"

# Classification results.
GMS_NONE = "none"
GMS_MICROG = "microg"
GMS_REAL = "gms"
GMS_UNKNOWN = "unknown"


def classify_gms_variant(adb: Adb) -> str:
    """Classify the installed GMS package.

    Returns one of: "none", "microg", "gms", "unknown".

    microG versionNames have always been 0.x, while real Play Services has
    shipped double-digit versions for over a decade, so the versionName
    prefix is a reliable discriminator.
    """
    return classify_package_variant(adb, GMS_PACKAGE)


def classify_package_variant(adb: Adb, package: str) -> str:
    """Classify a Google package id that microG may also occupy.

    microG's companion (FakeStore) installs as com.android.vending with a
    0.x versionName, the same way GmsCore takes the Play Services id, so
    the same discriminator applies.
    """
    if not adb.package_installed(package):
        return GMS_NONE
    try:
        dump = adb.shell(f"dumpsys package {package}")
    except AdbCommandError:
        return GMS_UNKNOWN
    for line in dump.splitlines():
        stripped = line.strip()
        if stripped.startswith("versionName="):
            version = stripped.split("=", 1)[1].strip()
            return GMS_MICROG if version.startswith("0.") else GMS_REAL
    return GMS_UNKNOWN
