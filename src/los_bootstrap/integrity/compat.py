"""App-compatibility matrix for German government / eID, health, and banking apps.

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
            "NFC-capable device to read the ID card. This covers reading the "
            "physical card only; see Smart-eID below."
        ),
        alternative="Desktop AusweisApp on Windows/macOS/Linux with a USB card reader.",
        last_verified=date(2026, 10, 11),
        source="f-droid.org listing (v2.5.5, 2026-08-17)",
    ),
    AppCompatEntry(
        name="Smart-eID (ID stored in the phone)",
        package="com.governikus.ausweisapp2",
        status=CompatLevel.BLOCKED,
        summary=(
            "Storing the ID in the phone instead of reading the card is not "
            "available on any ROM: the Interior Ministry halted the pilot in "
            "December 2023 for budget reasons and no relaunch was found. "
            "During the pilot it needed a certified secure element and ran "
            "only on a few Samsung Galaxy models."
        ),
        alternative="AusweisApp with the physical ID card over NFC, or a USB card reader on a desktop.",
        last_verified=date(2026, 11, 15),
        source="heise.de (2023-12-15); no later relaunch report found",
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
        name="AOK Mein Leben (ePA)",
        package="de.aok.digen",
        status=CompatLevel.BLOCKED,
        summary=(
            "Users on /e/OS and LineageOS report the app refusing to run with "
            "a 'modification of the operating system (e.g. rooting or "
            "jailbreak)' message, with the bootloader locked and unlocked "
            "alike, and with root hidden. AOK does not document the check. "
            "AOK requires Android 14 or newer since 2026-07-01."
        ),
        alternative=(
            "AOK ePA Desktop Client on a computer (aok.de says setup starts "
            "from the phone app; ask AOK support for a route without it)."
        ),
        last_verified=date(2025, 10, 24),
        source="community.e.foundation (2025-10-24, anecdotal); aok.de (updated 2026-11-12)",
    ),
    AppCompatEntry(
        name="BARMER eCare (ePA)",
        package="de.barmer.ecare",
        status=CompatLevel.BLOCKED,
        summary=(
            "BARMER states the device must not be rooted, must support the "
            "hardware Keystore, and needs Android 14 or newer. Its Meine "
            "BARMER app page lists LineageOS among alternative operating "
            "systems the app cannot be used with; eCare signs in through the "
            "same BARMER account."
        ),
        alternative=(
            "BARMER eCare for PC, signing in with the health card, its PIN "
            "and a card reader (no e-prescriptions or vaccination status)."
        ),
        last_verified=date(2026, 11, 15),
        source="barmer.de eCare page (updated 2026-11-10), Meine BARMER page (updated 2026-10-29)",
    ),
    AppCompatEntry(
        name="DAK App (ePA login)",
        package="de.dak.dak_app",
        status=CompatLevel.BLOCKED,
        summary=(
            "The Play Store listing names 'no rooted device' and 'no custom "
            "ROMs' as technical requirements. Users on GrapheneOS and "
            "LineageOS report the app refusing to start. The DAK ePA app and "
            "the web portal use this app as their second factor."
        ),
        alternative=(
            "No app-free login found. Use a stock-firmware second device, or "
            "contact the DAK ombudsman office for ePA objections and access "
            "settings."
        ),
        last_verified=date(2026, 11, 15),
        source="Google Play listing (checked 2026-11-15); kuketz-forum.de (2024, anecdotal)",
    ),
    AppCompatEntry(
        name="Das E-Rezept (gematik)",
        package="de.gematik.ti.erp.app",
        status=CompatLevel.WORKS,
        summary=(
            "gematik points users of 'free' Android systems to the APK on "
            "its GitHub releases; the app is not on F-Droid. An undated /e/OS "
            "report says it shows a rooted-device warning that can be "
            "accepted. Sign in with the health card and PIN over NFC; the "
            "GesundheitsID login goes through the insurer's app and is "
            "blocked wherever that app is."
        ),
        alternative=(
            "Hand over the health card at the pharmacy, or ask the practice "
            "for the paper printout with the prescription code."
        ),
        last_verified=date(2026, 11, 15),
        source="das-e-rezept-fuer-deutschland.de; gitlab.e.foundation issue 6899 (anecdotal)",
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
