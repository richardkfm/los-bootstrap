"""Flash lifecycle checks (Phase 11): ROM freshness + first-boot verification.

Pure core: the ``evaluate_*`` functions take already-collected data and
return result models. ``run_first_boot`` performs the few ADB probes a
fresh first boot needs, then delegates to the pure evaluator (the same
IO-at-the-edge split as ``audit/``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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


def evaluate_rom_update(
    facts: "DeviceFacts",
    latest: Optional[LineageBuild],
) -> RomUpdateResult:
    """Compare the device's LineageOS build against the latest official one.

    ``latest`` comes from ``lookup_lineage_build`` (``None`` when the API
    reports no builds for the codename). Network problems are surfaced by
    the caller; this function only compares build dates.
    """
    device_version = facts.lineage_version
    device_date = facts.build_date_utc

    if not facts.is_lineage:
        return RomUpdateResult(
            state=RomUpdateState.NOT_LINEAGEOS,
            device_version=device_version,
            device_build_date=device_date,
        )

    if latest is None:
        return RomUpdateResult(
            state=RomUpdateState.UNSUPPORTED,
            device_version=device_version,
            device_build_date=device_date,
        )

    if not device_date or device_date <= 0 or latest.datetime <= 0:
        return RomUpdateResult(
            state=RomUpdateState.UNVERIFIABLE,
            device_version=device_version,
            device_build_date=device_date,
            latest_version=latest.version,
            latest_build_date=latest.datetime,
            note="device build date (ro.build.date.utc) is not set",
        )

    days_behind = (
        (latest.datetime - device_date) // _DAY_SECONDS
        if latest.datetime > device_date
        else 0
    )
    if days_behind > 0:
        return RomUpdateResult(
            state=RomUpdateState.OUTDATED,
            device_version=device_version,
            device_build_date=device_date,
            latest_version=latest.version,
            latest_build_date=latest.datetime,
            days_behind=days_behind,
        )

    return RomUpdateResult(
        state=RomUpdateState.UP_TO_DATE,
        device_version=device_version,
        device_build_date=device_date,
        latest_version=latest.version,
        latest_build_date=latest.datetime,
        days_behind=0,
    )


# ---------------------------------------------------------------------------
# First-boot verification — `flash check`
# ---------------------------------------------------------------------------


def collect_first_boot_probes(adb: "Adb") -> FirstBootProbes:
    """Read the props a fresh first-boot check needs (all best-effort)."""
    verified_boot = ""
    build_type = ""
    slot_suffix = ""
    gms_present = False
    try:
        verified_boot = adb.getprop("ro.boot.verifiedbootstate")
    except Exception:
        pass
    try:
        build_type = adb.getprop("ro.build.type")
    except Exception:
        pass
    try:
        slot_suffix = adb.getprop("ro.boot.slot_suffix")
    except Exception:
        pass
    try:
        gms_present = adb.package_installed("com.google.android.gms")
    except Exception:
        pass
    return FirstBootProbes(
        verified_boot=verified_boot,
        build_type=build_type,
        slot_suffix=slot_suffix,
        gms_present=gms_present,
    )


def run_first_boot(adb: "Adb", facts: "DeviceFacts") -> FirstBootReport:
    """Probe the device and evaluate the first-boot checks."""
    return evaluate_first_boot(facts, collect_first_boot_probes(adb))


def evaluate_first_boot(
    facts: "DeviceFacts",
    probes: FirstBootProbes,
) -> FirstBootReport:
    """Pure evaluation of the first-boot checks against collected data."""
    findings: list[FirstBootFinding] = []

    if facts.is_lineage:
        findings.append(
            FirstBootFinding(
                check_id="fb.lineage",
                title="LineageOS detected",
                status=FirstBootStatus.PASS,
                detail=f"ro.lineage.version = {facts.lineage_version}",
            )
        )
    else:
        findings.append(
            FirstBootFinding(
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
        )

    fingerprint = facts.build_fingerprint
    if fingerprint.startswith("LineageOS/"):
        findings.append(
            FirstBootFinding(
                check_id="fb.fingerprint",
                title="Build fingerprint is a LineageOS build",
                status=FirstBootStatus.PASS,
                detail=fingerprint,
            )
        )
    elif facts.is_lineage:
        findings.append(
            FirstBootFinding(
                check_id="fb.fingerprint",
                title="Build fingerprint does not match LineageOS",
                status=FirstBootStatus.WARN,
                detail=f"ro.build.fingerprint = {fingerprint}",
                why=(
                    "ro.lineage.version says LineageOS but the fingerprint "
                    "disagrees; a mismatch can mean a modified flash or a "
                    "sister-distro build"
                ),
                fix_hint=(
                    "cross-check the build you flashed with `flash verify`, "
                    "or confirm the zip was an official LineageOS build"
                ),
            )
        )
    else:
        findings.append(
            FirstBootFinding(
                check_id="fb.fingerprint",
                title="Build fingerprint",
                status=FirstBootStatus.INFO,
                detail=f"ro.build.fingerprint = {fingerprint or '(empty)'}",
            )
        )

    vbs = probes.verified_boot.strip()
    vbs_lc = vbs.lower()
    if vbs_lc in ("green", "orange"):
        detail = f"ro.boot.verifiedbootstate = {vbs}"
        if vbs_lc == "orange":
            detail += " (self-attested — expected with an unlocked bootloader)"
        findings.append(
            FirstBootFinding(
                check_id="fb.verified_boot",
                title="Verified Boot state acceptable",
                status=FirstBootStatus.PASS,
                detail=detail,
            )
        )
    elif vbs_lc in ("yellow", "red"):
        findings.append(
            FirstBootFinding(
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
        )
    else:
        findings.append(
            FirstBootFinding(
                check_id="fb.verified_boot",
                title="No verified-boot state reported",
                status=FirstBootStatus.UNKNOWN,
                detail="ro.boot.verifiedbootstate is empty",
            )
        )

    if probes.slot_suffix:
        findings.append(
            FirstBootFinding(
                check_id="fb.slot",
                title="A/B slot active",
                status=FirstBootStatus.INFO,
                detail=probes.slot_suffix,
            )
        )
    else:
        findings.append(
            FirstBootFinding(
                check_id="fb.slot",
                title="A-only device",
                status=FirstBootStatus.INFO,
                detail="no ro.boot.slot_suffix set",
            )
        )

    if probes.gms_present:
        findings.append(
            FirstBootFinding(
                check_id="fb.gms",
                title="Google Play Services package present",
                status=FirstBootStatus.WARN,
                detail="com.google.android.gms is installed",
                why=(
                    "a fresh degoogled LineageOS flash should not ship GMS; "
                    "its presence here is either real GMS or the microG "
                    "replacement"
                ),
                fix_hint=(
                    "run `los-bootstrap location doctor` to classify which "
                    "one it is, then `los-bootstrap audit` for the privacy "
                    "posture"
                ),
            )
        )
    else:
        findings.append(
            FirstBootFinding(
                check_id="fb.gms",
                title="No GMS package present",
                status=FirstBootStatus.PASS,
                detail="com.google.android.gms is not installed, as expected after a degoogled flash",
            )
        )

    if probes.build_type:
        findings.append(
            FirstBootFinding(
                check_id="fb.build_type",
                title="Build type",
                status=FirstBootStatus.INFO,
                detail=(
                    f"ro.build.type = {probes.build_type} "
                    "(official LineageOS nightlies are userdebug)"
                ),
            )
        )

    return FirstBootReport(tuple(findings))
