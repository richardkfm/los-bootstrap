"""Flash lifecycle checks (Phase 11): ROM freshness + first-boot verification.

Pure core: ``evaluate_rom_update`` and the ``check_*`` functions take
already-collected data and return result models. ``collect_first_boot_probes``
performs the few ADB probes a fresh first boot needs and ``run_first_boot``
wires the two together — the same IO-at-the-edge split as ``audit/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterable, Optional, Sequence

from ..gms import GMS_MICROG, GMS_REAL, GMS_UNKNOWN, classify_gms_variant
from .distros import LineageBuild
from .models import (
    FirstBootFinding,
    FirstBootProbes,
    FirstBootReport,
    FirstBootStatus,
    RomUpdateResult,
    RomUpdateState,
)

if TYPE_CHECKING:
    from ..adb import Adb
    from ..device import DeviceFacts

_DAY_SECONDS = 86400


# ---------------------------------------------------------------------------
# ROM freshness — `flash update`
# ---------------------------------------------------------------------------


def major_version(version: Optional[str]) -> str:
    """Return the LineageOS major version as a string, or "" if unreadable.

    Accepts both API-shaped versions ("21.0", "22") and the device's
    ``ro.lineage.version`` ("21.0-20240101-NIGHTLY-panther").
    """
    if not version:
        return ""
    leading = version.strip().split("-", 1)[0]
    major = leading.split(".", 1)[0].strip()
    return major if major.isdigit() else ""


def pick_update_candidates(
    device_version: Optional[str],
    builds: Sequence[LineageBuild],
) -> tuple[Optional[LineageBuild], Optional[LineageBuild]]:
    """Split available builds into (same major version, newest overall).

    Freshness is judged against the device's own major version: telling a
    user on 21.x that they are "N days behind" a 22.x build conflates a
    nightly bump with a major upgrade that usually needs a full data wipe.
    The newest build overall is returned separately so the caller can
    mention the upgrade without confusing it with staleness.
    """
    usable = [b for b in builds if b.datetime > 0]
    if not usable:
        return None, None
    ordered = sorted(usable, key=lambda b: b.datetime, reverse=True)
    newest_overall = ordered[0]

    device_major = major_version(device_version)
    if not device_major:
        return newest_overall, newest_overall

    same_major = next(
        (b for b in ordered if major_version(b.version) == device_major), None
    )
    return same_major, newest_overall


def evaluate_rom_update(
    facts: "DeviceFacts",
    latest: Optional[LineageBuild],
    latest_overall: Optional[LineageBuild] = None,
    *,
    lookup_performed: bool = True,
    note: Optional[str] = None,
) -> RomUpdateResult:
    """Compare the device's LineageOS build against the latest official one.

    ``latest`` is the newest official build on the device's own major
    version; ``latest_overall`` (when given and newer-major) is reported as
    an available upgrade rather than as staleness. ``lookup_performed=False``
    means the API was never queried (``--no-network``), which is different
    from the API reporting no builds.
    """
    device_version = facts.lineage_version
    device_date = facts.build_date_utc

    if not facts.is_lineage:
        return RomUpdateResult(
            state=RomUpdateState.NOT_LINEAGEOS,
            device_version=device_version,
            device_build_date=device_date,
        )

    upgrade_version = None
    upgrade_build_date = None
    if latest_overall is not None:
        device_major = major_version(device_version)
        overall_major = major_version(latest_overall.version)
        if device_major and overall_major and overall_major > device_major:
            upgrade_version = latest_overall.version
            upgrade_build_date = latest_overall.datetime

    if not lookup_performed:
        return RomUpdateResult(
            state=RomUpdateState.UNVERIFIABLE,
            device_version=device_version,
            device_build_date=device_date,
            note=note or "the LineageOS API was not queried",
        )

    if latest is None:
        return RomUpdateResult(
            state=RomUpdateState.UNSUPPORTED,
            device_version=device_version,
            device_build_date=device_date,
            note=note,
            upgrade_version=upgrade_version,
            upgrade_build_date=upgrade_build_date,
        )

    if not device_date or device_date <= 0:
        reason = "device build date (ro.build.date.utc) is not set"
    elif latest.datetime <= 0:
        reason = "the LineageOS API did not report a build date for the latest build"
    else:
        reason = ""

    if reason:
        return RomUpdateResult(
            state=RomUpdateState.UNVERIFIABLE,
            device_version=device_version,
            device_build_date=device_date,
            latest_version=latest.version,
            latest_build_date=latest.datetime,
            note=note or reason,
            upgrade_version=upgrade_version,
            upgrade_build_date=upgrade_build_date,
        )

    # Compare the timestamps directly. Rounding to whole days first would
    # report a build that is 23 hours newer as "up to date".
    if latest.datetime > device_date:
        return RomUpdateResult(
            state=RomUpdateState.OUTDATED,
            device_version=device_version,
            device_build_date=device_date,
            latest_version=latest.version,
            latest_build_date=latest.datetime,
            days_behind=(latest.datetime - device_date) // _DAY_SECONDS,
            note=note,
            upgrade_version=upgrade_version,
            upgrade_build_date=upgrade_build_date,
        )

    return RomUpdateResult(
        state=RomUpdateState.UP_TO_DATE,
        device_version=device_version,
        device_build_date=device_date,
        latest_version=latest.version,
        latest_build_date=latest.datetime,
        days_behind=0,
        note=note,
        upgrade_version=upgrade_version,
        upgrade_build_date=upgrade_build_date,
    )


# ---------------------------------------------------------------------------
# First-boot verification — `flash check`
# ---------------------------------------------------------------------------

# Probe names, also used as the keys in FirstBootProbes.failed.
PROBE_VERIFIED_BOOT = "ro.boot.verifiedbootstate"
PROBE_BUILD_TYPE = "ro.build.type"
PROBE_SLOT_SUFFIX = "ro.boot.slot_suffix"
PROBE_GMS = "com.google.android.gms"


def collect_first_boot_probes(adb: "Adb") -> FirstBootProbes:
    """Read the props a fresh first-boot check needs (all best-effort).

    Every probe that raises is recorded in ``failed`` so the evaluator can
    tell "not present" apart from "could not ask".
    """
    failed: list[str] = []

    def _prop(name: str) -> str:
        try:
            return adb.getprop(name)
        except Exception:
            failed.append(name)
            return ""

    verified_boot = _prop(PROBE_VERIFIED_BOOT)
    build_type = _prop(PROBE_BUILD_TYPE)
    slot_suffix = _prop(PROBE_SLOT_SUFFIX)

    try:
        gms_variant = classify_gms_variant(adb)
    except Exception:
        failed.append(PROBE_GMS)
        gms_variant = GMS_UNKNOWN

    return FirstBootProbes(
        verified_boot=verified_boot,
        build_type=build_type,
        slot_suffix=slot_suffix,
        gms_variant=gms_variant,
        failed=tuple(failed),
    )


def check_probe_health(
    _facts: "DeviceFacts", probes: FirstBootProbes
) -> Iterable[FirstBootFinding]:
    """Report probes that could not be read at all."""
    if not probes.failed:
        return
    yield FirstBootFinding(
        check_id="fb.probes",
        title="Some device properties could not be read",
        status=FirstBootStatus.UNKNOWN,
        detail="failed probes: " + ", ".join(probes.failed),
        why=(
            "the checks below are incomplete — an unreadable probe is not "
            "the same as a clean result"
        ),
        fix_hint=(
            "re-check the USB connection and the ADB authorization prompt, "
            "then run `los-bootstrap flash check` again"
        ),
    )


def check_lineage(
    facts: "DeviceFacts", _probes: FirstBootProbes
) -> Iterable[FirstBootFinding]:
    if facts.is_lineage:
        yield FirstBootFinding(
            check_id="fb.lineage",
            title="LineageOS detected",
            status=FirstBootStatus.PASS,
            detail=f"ro.lineage.version = {facts.lineage_version}",
        )
        return
    yield FirstBootFinding(
        check_id="fb.lineage",
        title="LineageOS not detected",
        status=FirstBootStatus.FAIL,
        detail=(
            "ro.lineage.version is empty — the device does not "
            "report a LineageOS build"
        ),
        why="flash check verifies a fresh LineageOS install; any other OS is out of scope",
        fix_hint=(
            "if the device just finished flashing, wait for the "
            "first-boot setup to complete; if it never reaches "
            "Android, the flash did not take — re-verify the ROM "
            "zip (`flash verify`) and re-run `flash run`"
        ),
    )


def check_fingerprint(
    facts: "DeviceFacts", _probes: FirstBootProbes
) -> Iterable[FirstBootFinding]:
    """Report the build fingerprint.

    `ro.build.fingerprint` follows the AOSP shape
    brand/product/device:release/id/incremental:type/tags, and LineageOS
    builds carry `lineage_<codename>` in the product segment. Many ROMs
    deliberately spoof a stock fingerprint, so a fingerprint that does not
    name LineageOS is informational — `ro.lineage.version` is the
    authoritative signal, and this must not gate the exit code.
    """
    fingerprint = facts.build_fingerprint
    if "lineage" in fingerprint.lower():
        yield FirstBootFinding(
            check_id="fb.fingerprint",
            title="Build fingerprint is a LineageOS build",
            status=FirstBootStatus.PASS,
            detail=fingerprint,
        )
        return

    if facts.is_lineage:
        yield FirstBootFinding(
            check_id="fb.fingerprint",
            title="Build fingerprint does not name LineageOS",
            status=FirstBootStatus.INFO,
            detail=f"ro.build.fingerprint = {fingerprint or '(empty)'}",
            why=(
                "ro.lineage.version already identifies this as LineageOS. "
                "Many builds spoof a stock fingerprint on purpose, so this "
                "on its own is not a sign of a bad flash"
            ),
        )
        return

    yield FirstBootFinding(
        check_id="fb.fingerprint",
        title="Build fingerprint",
        status=FirstBootStatus.INFO,
        detail=f"ro.build.fingerprint = {fingerprint or '(empty)'}",
    )


def check_verified_boot(
    _facts: "DeviceFacts", probes: FirstBootProbes
) -> Iterable[FirstBootFinding]:
    if probes.probe_failed(PROBE_VERIFIED_BOOT):
        yield FirstBootFinding(
            check_id="fb.verified_boot",
            title="Verified Boot state could not be read",
            status=FirstBootStatus.UNKNOWN,
            detail=f"{PROBE_VERIFIED_BOOT} could not be queried",
        )
        return

    vbs = probes.verified_boot.strip()
    vbs_lc = vbs.lower()
    if vbs_lc in ("green", "orange"):
        detail = f"ro.boot.verifiedbootstate = {vbs}"
        if vbs_lc == "orange":
            detail += " (self-attested — expected with an unlocked bootloader)"
        yield FirstBootFinding(
            check_id="fb.verified_boot",
            title="Verified Boot state acceptable",
            status=FirstBootStatus.PASS,
            detail=detail,
        )
    elif vbs_lc in ("yellow", "red"):
        yield FirstBootFinding(
            check_id="fb.verified_boot",
            title="Verified Boot reported a failure",
            status=FirstBootStatus.FAIL,
            detail=f"ro.boot.verifiedbootstate = {vbs}",
            why=(
                "yellow or red means the boot image failed integrity "
                "verification; right after a flash this most often "
                "means a ROM or boot image for the wrong device"
            ),
            fix_hint=(
                "stop and re-check the zip with `flash verify` against "
                "the device codename, then re-flash — do not continue "
                "setting up this build"
            ),
        )
    else:
        yield FirstBootFinding(
            check_id="fb.verified_boot",
            title="No verified-boot state reported",
            status=FirstBootStatus.UNKNOWN,
            detail="ro.boot.verifiedbootstate is empty",
        )


def check_slot(
    _facts: "DeviceFacts", probes: FirstBootProbes
) -> Iterable[FirstBootFinding]:
    if probes.probe_failed(PROBE_SLOT_SUFFIX):
        yield FirstBootFinding(
            check_id="fb.slot",
            title="A/B slot could not be read",
            status=FirstBootStatus.UNKNOWN,
            detail=f"{PROBE_SLOT_SUFFIX} could not be queried",
        )
    elif probes.slot_suffix:
        yield FirstBootFinding(
            check_id="fb.slot",
            title="A/B slot active",
            status=FirstBootStatus.INFO,
            detail=probes.slot_suffix,
        )
    else:
        yield FirstBootFinding(
            check_id="fb.slot",
            title="A-only device",
            status=FirstBootStatus.INFO,
            detail="no ro.boot.slot_suffix set",
        )


def check_gms(
    _facts: "DeviceFacts", probes: FirstBootProbes
) -> Iterable[FirstBootFinding]:
    """Classify the GMS package rather than merely detecting it.

    microG registers the real Play Services package id by design, so
    presence alone would flag every LineageOS-for-microG device.
    """
    if probes.probe_failed(PROBE_GMS) or probes.gms_variant == GMS_UNKNOWN:
        yield FirstBootFinding(
            check_id="fb.gms",
            title="Could not determine whether Play Services is present",
            status=FirstBootStatus.UNKNOWN,
            detail=f"{PROBE_GMS} could not be classified",
            why=(
                "this is not the same as 'no GMS present' — the check simply "
                "could not be completed"
            ),
            fix_hint=(
                "run `los-bootstrap location doctor` once the device is "
                "responding again"
            ),
        )
    elif probes.gms_variant == GMS_REAL:
        yield FirstBootFinding(
            check_id="fb.gms",
            title="Real Google Play Services is installed",
            status=FirstBootStatus.WARN,
            detail=f"{PROBE_GMS} reports a Play Services versionName",
            why=(
                "a fresh degoogled LineageOS flash should not ship real GMS; "
                "its presence means the build is not degoogled"
            ),
            fix_hint=(
                "run `los-bootstrap audit` for the full privacy posture, and "
                "confirm you flashed the build you intended to"
            ),
        )
    elif probes.gms_variant == GMS_MICROG:
        yield FirstBootFinding(
            check_id="fb.gms",
            title="microG is installed (not real Play Services)",
            status=FirstBootStatus.PASS,
            detail=f"{PROBE_GMS} reports a microG versionName (0.x)",
        )
    else:  # GMS_NONE
        yield FirstBootFinding(
            check_id="fb.gms",
            title="No GMS package present",
            status=FirstBootStatus.PASS,
            detail=f"{PROBE_GMS} is not installed, as expected after a degoogled flash",
        )


def check_build_type(
    _facts: "DeviceFacts", probes: FirstBootProbes
) -> Iterable[FirstBootFinding]:
    if not probes.build_type:
        return
    yield FirstBootFinding(
        check_id="fb.build_type",
        title="Build type",
        status=FirstBootStatus.INFO,
        detail=(
            f"ro.build.type = {probes.build_type} "
            "(official LineageOS nightlies are userdebug)"
        ),
    )


FirstBootCheckFn = Callable[
    ["DeviceFacts", FirstBootProbes], Iterable[FirstBootFinding]
]

FIRST_BOOT_CHECKS: tuple[FirstBootCheckFn, ...] = (
    check_probe_health,
    check_lineage,
    check_fingerprint,
    check_verified_boot,
    check_slot,
    check_gms,
    check_build_type,
)


def evaluate_first_boot(
    facts: "DeviceFacts",
    probes: FirstBootProbes,
) -> FirstBootReport:
    """Pure evaluation of the first-boot checks against collected data."""
    findings: list[FirstBootFinding] = []
    for check in FIRST_BOOT_CHECKS:
        findings.extend(check(facts, probes))
    return FirstBootReport(tuple(findings))


def run_first_boot(adb: "Adb", facts: "DeviceFacts") -> FirstBootReport:
    """Probe the device and evaluate the first-boot checks."""
    return evaluate_first_boot(facts, collect_first_boot_probes(adb))
