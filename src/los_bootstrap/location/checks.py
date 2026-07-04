"""Location stack diagnostics — read-only ADB queries with rationale and tradeoffs.

Every check must document *why* the component matters and *what the user gives up*
by not having it. Mirrors the harden/ philosophy: no recommendation without a downside.

All checks are read-only. No state is mutated.
"""

from __future__ import annotations

from typing import Callable, Iterable

from ..adb import Adb, AdbCommandError
from ..device import DeviceFacts
from .models import LocationFinding, LocationReport, LocationStatus


LocationCheckFn = Callable[[Adb, DeviceFacts], Iterable[LocationFinding]]

# microG GmsCore installs under the real Play Services package id — that is
# the whole point of microG — so presence alone cannot distinguish the two.
GMS_PACKAGE = "com.google.android.gms"


def _gms_variant(adb: Adb) -> str:
    """Classify the installed com.google.android.gms package.

    Returns one of: "none", "microg", "gms", "unknown".

    microG versionNames have always been 0.x, while real Play Services has
    shipped double-digit versions for over a decade, so the versionName
    prefix is a reliable discriminator.
    """
    if not adb.package_installed(GMS_PACKAGE):
        return "none"
    try:
        dump = adb.shell(f"dumpsys package {GMS_PACKAGE}")
    except AdbCommandError:
        return "unknown"
    for line in dump.splitlines():
        stripped = line.strip()
        if stripped.startswith("versionName="):
            version = stripped.split("=", 1)[1].strip()
            return "microg" if version.startswith("0.") else "gms"
    return "unknown"


# Known UnifiedNlp / microG network-location backend packages.
# Each tuple is (package_name, human_readable_description).
_KNOWN_BACKENDS: tuple[tuple[str, str], ...] = (
    (
        "org.microg.nlp.backend.ichnaea",
        "Mozilla Location Service (MLS) — online, community-run, privacy-friendly",
    ),
    (
        "org.fitchfamily.android.dejavu",
        "DejaVu — offline, builds a private local RF map; no remote calls",
    ),
    (
        "org.microg.nlp.backend.apple",
        "Apple WiFi/Cell — online; accurate but routes data through Apple servers",
    ),
    (
        "org.openbmap.unifiedNlp",
        "Radiocells.org — online, crowdsourced cell-tower database",
    ),
    (
        "org.microg.nlp.backend.nominatim",
        "Nominatim — geocoder (address → coordinates); not a position source",
    ),
)


def check_location_enabled(adb: Adb, _facts: DeviceFacts) -> Iterable[LocationFinding]:
    """Check whether the system location master switch is on."""
    raw = adb.shell("settings get secure location_enabled").strip()
    if raw in ("0", "1"):
        enabled = raw == "1"
        detail = f"settings secure location_enabled = {raw!r}"
    else:
        # Android < 9 used location_providers_allowed; check for any entry.
        try:
            providers = adb.shell("settings get secure location_providers_allowed").strip()
        except AdbCommandError:
            providers = ""
        enabled = bool(providers) and providers.lower() not in ("null", "")
        detail = f"location_providers_allowed = {providers!r}"

    yield LocationFinding(
        check_id="loc.enabled",
        title="Location " + ("enabled" if enabled else "disabled"),
        status=LocationStatus.PASS if enabled else LocationStatus.FAIL,
        detail=detail,
        why=(
            "Location must be on for GPS, network, and passive providers to function. "
            "With it off, every app requesting a location fix receives nothing, "
            "regardless of what backends or microG are installed."
        ),
        tradeoff=(
            "Enabling location allows apps with ACCESS_FINE_LOCATION or "
            "ACCESS_COARSE_LOCATION permission to request your position. "
            "Only apps individually granted that permission receive results."
        ),
        fix_hint="Settings > Location > Use location — toggle on.",
    )


def check_microg_core(adb: Adb, _facts: DeviceFacts) -> Iterable[LocationFinding]:
    """Check whether microG GmsCore is installed."""
    variant = _gms_variant(adb)
    if variant == "unknown":
        yield LocationFinding(
            check_id="loc.microg_core",
            title="microG GmsCore: could not classify the installed GMS package",
            status=LocationStatus.UNKNOWN,
            detail=(
                f"{GMS_PACKAGE} is installed but its versionName could not be "
                "read; unable to tell microG from real Play Services."
            ),
            why=(
                "microG installs under the real Play Services package id, so "
                "the versionName is needed to distinguish the two."
            ),
            tradeoff="N/A",
            fix_hint=(
                f"Inspect manually: adb shell dumpsys package {GMS_PACKAGE} "
                "| grep versionName — microG reports 0.x versions."
            ),
        )
        return
    installed = variant == "microg"
    if variant == "gms":
        detail = f"{GMS_PACKAGE} is installed but is real Play Services, not microG."
    else:
        detail = (
            f"{GMS_PACKAGE} → {'microG versionName (0.x) detected' if installed else 'not found'}"
        )
    yield LocationFinding(
        check_id="loc.microg_core",
        title="microG GmsCore " + ("installed" if installed else "not installed"),
        status=LocationStatus.PASS if installed else LocationStatus.INFO,
        detail=detail,
        why=(
            "microG is a free-software reimplementation of Google Play Services. "
            "It exposes the FusedLocationProvider API that many apps call instead "
            "of the OS location stack. Without microG, those apps cannot obtain "
            "a fix at all, even if GPS hardware is present and working."
        ),
        tradeoff=(
            "microG must be granted signature spoofing (a ROM-level patch) to "
            "fully replace GMS for apps that verify the GMS package identity. "
            "Installing microG without spoofing gives partial benefit only. "
            "microG runs as a background service and increases the system attack surface."
        ),
        fix_hint=(
            "Install microG GmsCore from the microG F-Droid repository. "
            "Your ROM must support signature spoofing; verify with "
            "`los-bootstrap location doctor` after installing."
        ),
    )


def check_signature_spoofing(adb: Adb, _facts: DeviceFacts) -> Iterable[LocationFinding]:
    """Check whether microG has the FAKE_PACKAGE_SIGNATURE permission granted."""
    if _gms_variant(adb) != "microg":
        yield LocationFinding(
            check_id="loc.sig_spoof",
            title="Signature spoofing: microG not installed — check skipped",
            status=LocationStatus.INFO,
            detail="No microG GmsCore found; spoofing check requires microG.",
            why=(
                "Signature spoofing lets microG masquerade as Google Play Services. "
                "Without it, apps that verify the GMS package signature will reject "
                "microG and fail to use it as a location provider."
            ),
            tradeoff=(
                "Spoofing is a deliberate ROM-level capability. It must be granted "
                "only to trusted system apps; granting it broadly would weaken "
                "Android's package-identity guarantees."
            ),
            fix_hint="Install microG first, then re-run `location doctor`.",
        )
        return

    try:
        dump = adb.shell(f"pm dump {GMS_PACKAGE}")
    except AdbCommandError:
        yield LocationFinding(
            check_id="loc.sig_spoof",
            title="Signature spoofing: could not inspect microG permissions",
            status=LocationStatus.UNKNOWN,
            detail=f"pm dump {GMS_PACKAGE} failed.",
            why="FAKE_PACKAGE_SIGNATURE is needed for microG to fully replace GMS.",
            tradeoff="N/A",
            fix_hint=f"Run `adb shell pm dump {GMS_PACKAGE}` manually to inspect.",
        )
        return

    has_spoof = "FAKE_PACKAGE_SIGNATURE" in dump
    yield LocationFinding(
        check_id="loc.sig_spoof",
        title="Signature spoofing: "
        + ("granted to microG" if has_spoof else "NOT granted to microG"),
        status=LocationStatus.PASS if has_spoof else LocationStatus.WARN,
        detail=f"FAKE_PACKAGE_SIGNATURE in pm dump: {'yes' if has_spoof else 'no'}",
        why=(
            "Without FAKE_PACKAGE_SIGNATURE, apps that call "
            "PackageManager.getPackageInfo() to verify they're talking to real "
            "Play Services will reject microG, breaking Fused Location for those apps."
        ),
        tradeoff=(
            "Signature spoofing is a ROM-level feature; it cannot be added via ADB "
            "on an unpatched ROM. Accepting it means the ROM weakens package-identity "
            "guarantees for the specific apps that are granted the permission."
        ),
        fix_hint=(
            "Your ROM must include the signature-spoofing patch (e.g. LineageOS for "
            "microG, CalyxOS, DivestOS). This cannot be enabled via ADB. "
            "Alternatively, check microG Settings > Self-Check to see if the ROM "
            "exposes a grant path."
        ),
    )


def check_nlp_backends(adb: Adb, _facts: DeviceFacts) -> Iterable[LocationFinding]:
    """Check which network location backends (UnifiedNlp) are installed."""
    found: list[tuple[str, str]] = []
    for pkg, desc in _KNOWN_BACKENDS:
        if adb.package_installed(pkg):
            found.append((pkg, desc))

    if found:
        descriptions = "; ".join(f"{pkg}: {desc}" for pkg, desc in found)
        yield LocationFinding(
            check_id="loc.nlp_backends",
            title=f"Network location backends: {len(found)} installed",
            status=LocationStatus.PASS,
            detail=descriptions,
            why=(
                "Network location backends estimate position from WiFi access points "
                "and cell towers without GPS hardware, enabling faster first-fix and "
                "indoor positioning. microG's UnifiedNlp routes requests to them."
            ),
            tradeoff=(
                "Online backends (Mozilla MLS, Apple) send observed WiFi/cell data to "
                "a remote server. DejaVu is fully offline and private but needs time to "
                "build a local RF map before it can provide fixes."
            ),
            fix_hint="",
        )
    else:
        yield LocationFinding(
            check_id="loc.nlp_backends",
            title="Network location backends: none installed",
            status=LocationStatus.INFO,
            detail="None of the known NLP backend packages were found on the device.",
            why=(
                "Without a network location backend, microG cannot provide WiFi- or "
                "cell-assisted location. Apps relying on FusedLocation get GPS fixes "
                "only, which are slower to acquire and unavailable indoors."
            ),
            tradeoff=(
                "DejaVu (offline) adds no remote telemetry and is the privacy-preserving "
                "choice. Mozilla Ichnaea (MLS) is online but community-run. "
                "The tradeoff is fix speed vs. privacy: offline backends are private "
                "but require warm-up time to build a local database."
            ),
            fix_hint=(
                "Recommended: install DejaVu (org.fitchfamily.android.dejavu) from "
                "F-Droid for offline-only operation. Add Mozilla Ichnaea "
                "(org.microg.nlp.backend.ichnaea) as a second backend if faster "
                "initial fixes are more important than avoiding remote calls."
            ),
        )


def check_real_gms_conflict(adb: Adb, _facts: DeviceFacts) -> Iterable[LocationFinding]:
    """Check whether real Google Play Services is installed — it conflicts with microG."""
    variant = _gms_variant(adb)
    if variant == "microg":
        yield LocationFinding(
            check_id="loc.gms_conflict",
            title="Real Google Play Services not detected (microG occupies the package)",
            status=LocationStatus.PASS,
            detail=f"{GMS_PACKAGE} is present but its versionName identifies it as microG.",
            why=(
                "microG deliberately installs under the Play Services package id; "
                "this is not a conflict but the intended degoogled configuration."
            ),
            tradeoff="None.",
            fix_hint="",
        )
        return
    if variant == "unknown":
        yield LocationFinding(
            check_id="loc.gms_conflict",
            title="A GMS-compatible core is installed but could not be classified",
            status=LocationStatus.UNKNOWN,
            detail=f"{GMS_PACKAGE} is installed; versionName could not be read.",
            why=(
                "microG and real Google Play Services share the same package id. "
                "Without the versionName, this tool cannot tell which is installed."
            ),
            tradeoff="N/A",
            fix_hint=(
                f"Inspect manually: adb shell dumpsys package {GMS_PACKAGE} "
                "| grep versionName — microG reports 0.x versions."
            ),
        )
        return
    if variant == "gms":
        yield LocationFinding(
            check_id="loc.gms_conflict",
            title="Real Google Play Services detected — may conflict with microG",
            status=LocationStatus.WARN,
            detail=f"pm list packages {GMS_PACKAGE} → found (non-microG versionName)",
            why=(
                "microG and real Google Play Services cannot coexist as location providers. "
                "If both are present, location requests may be silently routed to GMS, "
                "defeating the degoogled setup."
            ),
            tradeoff=(
                "Removing GMS breaks all apps that depend on it unless microG provides "
                "adequate coverage. Only do this on a ROM explicitly built for microG."
            ),
            fix_hint=(
                "Run `adb shell pm list packages -f com.google.android.gms` to check "
                "the APK path. On some ROMs the package is a harmless stub under "
                "/system/app/; verify before drawing conclusions."
            ),
        )
    else:
        yield LocationFinding(
            check_id="loc.gms_conflict",
            title="Real Google Play Services not detected",
            status=LocationStatus.PASS,
            detail="pm list packages com.google.android.gms → not found",
            why=(
                "Absence of real GMS means microG can operate as the sole GMS "
                "replacement without a conflicting implementation."
            ),
            tradeoff="None.",
            fix_hint="",
        )


# ── Orchestrator ──────────────────────────────────────────────────────────────

CHECKS: tuple[LocationCheckFn, ...] = (
    check_location_enabled,
    check_real_gms_conflict,
    check_microg_core,
    check_signature_spoofing,
    check_nlp_backends,
)


def run_location_doctor(adb: Adb, facts: DeviceFacts) -> LocationReport:
    findings: list[LocationFinding] = []
    for check in CHECKS:
        findings.extend(check(adb, facts))
    return LocationReport(findings=tuple(findings))
