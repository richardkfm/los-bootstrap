"""App compatibility matrix for location functionality on degoogled ROMs.

Static, human-maintained data. Accuracy matters more than coverage.
Add only entries with known, verified behaviour on real microG + LineageOS setups.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class CompatLevel(str, Enum):
    YES = "yes"        # works fully without GMS or microG
    GPS_ONLY = "gps-only"  # GPS-based location works; network location absent or degraded
    PARTIAL = "partial"    # needs microG for full location functionality
    NO = "no"              # will not work even with microG; requires real GMS


@dataclass(frozen=True)
class AppCompatEntry:
    name: str
    package: str        # Android package name; "(various)" for categories
    status: CompatLevel
    summary: str        # one-line explanation of the limitation or pass
    microg_helps: bool  # True if adding microG meaningfully improves this app


# Entries are grouped by category for readability in the rendered output.
# Each entry reflects real-world microG + LineageOS usage. Do not add entries
# without a concrete reference or test.
COMPAT_MATRIX: Tuple[AppCompatEntry, ...] = (
    # Maps / navigation
    AppCompatEntry(
        name="OsmAnd",
        package="net.osmand",
        status=CompatLevel.YES,
        summary="Full offline maps + GPS routing. No GMS or network location needed.",
        microg_helps=False,
    ),
    AppCompatEntry(
        name="Organic Maps",
        package="app.organicmaps",
        status=CompatLevel.YES,
        summary="Offline maps + GPS routing. Fully works without GMS.",
        microg_helps=False,
    ),
    AppCompatEntry(
        name="Magic Earth",
        package="com.generalmagic.magicearth",
        status=CompatLevel.GPS_ONLY,
        summary="GPS routing works. Traffic and online search degrade without network location.",
        microg_helps=True,
    ),
    AppCompatEntry(
        name="Google Maps",
        package="com.google.android.apps.maps",
        status=CompatLevel.NO,
        summary="Requires real GMS. Use OsmAnd or Organic Maps instead.",
        microg_helps=False,
    ),
    # Messaging
    AppCompatEntry(
        name="Telegram",
        package="org.telegram.messenger",
        status=CompatLevel.YES,
        summary="Location share and live location work via GPS alone.",
        microg_helps=False,
    ),
    AppCompatEntry(
        name="Signal",
        package="org.thoughtcrime.securesms",
        status=CompatLevel.YES,
        summary="Location share works via GPS only. No GMS dependency.",
        microg_helps=False,
    ),
    AppCompatEntry(
        name="WhatsApp",
        package="com.whatsapp",
        status=CompatLevel.PARTIAL,
        summary="Location share calls FusedLocationProvider — needs microG for reliability.",
        microg_helps=True,
    ),
    AppCompatEntry(
        name="Element (Matrix)",
        package="im.vector.app",
        status=CompatLevel.YES,
        summary="Location share uses GPS via OSM tiles. No GMS needed.",
        microg_helps=False,
    ),
    # Browsers
    AppCompatEntry(
        name="Firefox",
        package="org.mozilla.firefox",
        status=CompatLevel.YES,
        summary="HTML5 Geolocation API works via GPS. microG adds WiFi-assisted location.",
        microg_helps=True,
    ),
    AppCompatEntry(
        name="Brave",
        package="com.brave.browser",
        status=CompatLevel.YES,
        summary="Uses system location directly; GPS works. microG improves first-fix time.",
        microg_helps=True,
    ),
    AppCompatEntry(
        name="Chromium / Vanadium",
        package="org.chromium.chrome",
        status=CompatLevel.PARTIAL,
        summary="HTML5 Geolocation API calls FusedLocationProvider → needs microG.",
        microg_helps=True,
    ),
    # Ride-sharing / delivery
    AppCompatEntry(
        name="Uber / Lyft",
        package="(proprietary)",
        status=CompatLevel.PARTIAL,
        summary="GPS works but Play Integrity checks often block service on degoogled ROMs.",
        microg_helps=True,
    ),
    # Utilities
    AppCompatEntry(
        name="F-Droid",
        package="org.fdroid.fdroid",
        status=CompatLevel.YES,
        summary="No location dependency whatsoever.",
        microg_helps=False,
    ),
    AppCompatEntry(
        name="Weather apps (most)",
        package="(various)",
        status=CompatLevel.GPS_ONLY,
        summary="GPS-based current-location works. Some use FusedLocation for faster fix.",
        microg_helps=True,
    ),
)
