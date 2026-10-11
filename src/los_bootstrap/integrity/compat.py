"""App-compatibility matrix for German government / eID and banking apps.

Static, human-maintained data. Accuracy matters more than coverage. Every
entry records when it was last verified; the renderer downgrades anything
older than STALE_AFTER_DAYS to "unverified" rather than presenting aged
hearsay as current fact.

Sources are forum reports and vendor statements, both of which drift. When
in doubt the status is UNKNOWN. This data never claims an app "works" on the
strength of a single old post.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional, Tuple


STALE_AFTER_DAYS = 183  # ~6 months


class CompatLevel(str, Enum):
    WORKS = "works"          # runs on a degoogled ROM as-is
    MICROG = "microg"        # runs once microG is installed; no verdict needed
    SPOOF = "spoof"          # needs Play Integrity spoofing (root)
    BLOCKED = "blocked"      # no on-device workaround; use the alternative
    UNKNOWN = "unknown"      # not reliably verified


@dataclass(frozen=True)
class AppCompatEntry:
    name: str
    package: str
    status: CompatLevel
    summary: str
    alternative: str          # non-phone route (web / desktop / card reader)
    last_verified: Optional[date]
    source: str               # where the status came from


COMPAT_MATRIX: Tuple[AppCompatEntry, ...] = (
    AppCompatEntry(
        name="AusweisApp (eID)",
        package="com.governikus.ausweisapp2",
        status=CompatLevel.WORKS,
        summary=(
            "Official German eID app. Published on F-Droid with no listed "
            "anti-features; does not require Google Play services. Needs an "
            "NFC-capable device to read the ID card."
        ),
        alternative="Desktop AusweisApp on Windows/macOS/Linux with a USB card reader.",
        last_verified=date(2026, 10, 11),
        source="f-droid.org listing (v2.5.5, 2026-08-17)",
    ),
    AppCompatEntry(
        name="TK-App (ePA)",
        package="com.ibm.ega.tk",
        status=CompatLevel.BLOCKED,
        summary=(
            "Techniker Krankenkasse app runs a mobile-device attestation and "
            "excludes unlocked bootloaders and rooted devices. GrapheneOS is "
            "explicitly allowed if its integrity check passes; LineageOS is "
            "not supported. Biometric login and push still need Play services."
        ),
        alternative="'Meine TK' web application; TK-Safe (ePA) on a computer.",
        last_verified=date(2026, 10, 8),
        source="tk.de app-support page (dated 2026-10-08)",
    ),
    AppCompatEntry(
        name="ElsterSmart (tax)",
        package="de.elster.elstersmart",
        status=CompatLevel.UNKNOWN,
        summary=(
            "Users report failures on custom ROMs (error 611003) with no "
            "vendor fix; the detection mechanism is not confirmed. Treat as "
            "unverified until tested on a current build."
        ),
        alternative="Mein ELSTER in a desktop browser with the ElsterSecure certificate file.",
        last_verified=None,
        source="forum.elster.de (anecdotal, undated)",
    ),
    AppCompatEntry(
        name="Sparkasse S-pushTAN",
        package="com.starfinanz.mobile.android.pushtan",
        status=CompatLevel.BLOCKED,
        summary=(
            "Reported to refuse service and to flag devices as rooted on "
            "custom ROMs, in some cases even with the bootloader locked. An "
            "older app version installed via Aurora Store reportedly still "
            "ran; current versions do not. Mechanism unconfirmed."
        ),
        alternative="Sparkasse online banking in a browser; chipTAN with a card reader.",
        last_verified=None,
        source="community.e.foundation, forum.fairphone.com (anecdotal)",
    ),
    AppCompatEntry(
        name="DB Navigator",
        package="de.hafas.android.db",
        status=CompatLevel.MICROG,
        summary=(
            "Reported to work on LineageOS with microG; maps and push "
            "notifications need microG, core booking works without it. No "
            "integrity gate observed. Reports are several years old."
        ),
        alternative="bahn.de in a browser for booking and tickets.",
        last_verified=None,
        source="forum.f-droid.org (anecdotal, dated)",
    ),
    AppCompatEntry(
        name="VR SecureGo plus",
        package="de.fiducia.smartphone.android.securego.vr",
        status=CompatLevel.UNKNOWN,
        summary=(
            "Volksbank/Raiffeisen TAN app. No reliable report on custom-ROM "
            "or root behaviour was found; status not verified."
        ),
        alternative="VR online banking in a browser; ask your bank about a TAN generator.",
        last_verified=None,
        source="no verified source",
    ),
)
