"""Individual audit checks plus the orchestrator.

Each check takes the `Adb` wrapper plus already-collected `DeviceFacts`
and returns zero or more `AuditFinding`s. Checks must be read-only.
"""

from __future__ import annotations

from typing import Callable, Iterable

from ..adb import Adb
from ..device import DeviceFacts
from .models import AuditFinding, AuditReport, Severity


# Packages we care about. Keep this list short and curated; long lists
# rot fast and add noise. Phase 2 can move this to a YAML profile.
GMS_PACKAGE = "com.google.android.gms"
GSF_PACKAGE = "com.google.android.gsf"

COMMON_GOOGLE_PACKAGES = (
    "com.android.vending",            # Play Store
    "com.google.android.apps.maps",   # Maps
    "com.google.android.gm",          # Gmail
    "com.google.android.youtube",     # YouTube
    "com.google.android.inputmethod.latin",  # Gboard
)


CheckFn = Callable[[Adb, DeviceFacts], Iterable[AuditFinding]]


def check_lineage_identity(_adb: Adb, facts: DeviceFacts) -> Iterable[AuditFinding]:
    if facts.is_lineage:
        yield AuditFinding(
            check="rom.lineage",
            title="LineageOS detected",
            severity=Severity.INFO,
            detail=f"ro.lineage.version = {facts.lineage_version!r}.",
        )
    else:
        yield AuditFinding(
            check="rom.lineage",
            title="Not a LineageOS build",
            severity=Severity.INFO,
            detail=(
                "No ro.lineage.version property found. los-bootstrap will "
                "still work on AOSP-derived ROMs, but device-specific "
                "guidance assumes LineageOS conventions."
            ),
        )


def check_gms(adb: Adb, _facts: DeviceFacts) -> Iterable[AuditFinding]:
    if adb.package_installed(GMS_PACKAGE):
        yield AuditFinding(
            check="gms.present",
            title="Google Mobile Services is installed",
            severity=Severity.WARN,
            detail=(
                f"{GMS_PACKAGE} is installed. This indicates a GApps build "
                "or microG. If you intended a fully degoogled setup, "
                "investigate which build was flashed."
            ),
            recommendation=(
                "If unintended: reflash a vanilla LineageOS build. If this "
                "is microG, ignore this finding."
            ),
        )
    else:
        yield AuditFinding(
            check="gms.present",
            title="No Google Mobile Services",
            severity=Severity.OK,
            detail=f"{GMS_PACKAGE} is not installed. Degoogled-friendly.",
        )


def check_gsf(adb: Adb, _facts: DeviceFacts) -> Iterable[AuditFinding]:
    if adb.package_installed(GSF_PACKAGE):
        yield AuditFinding(
            check="gsf.present",
            title="Google Services Framework is installed",
            severity=Severity.WARN,
            detail=f"{GSF_PACKAGE} is installed.",
            recommendation="See GMS guidance — same root cause.",
        )


def check_common_google_packages(adb: Adb, _facts: DeviceFacts) -> Iterable[AuditFinding]:
    found = [p for p in COMMON_GOOGLE_PACKAGES if adb.package_installed(p)]
    if not found:
        yield AuditFinding(
            check="google.client_packages",
            title="No common Google client packages installed",
            severity=Severity.OK,
            detail="None of the curated Google client packages were detected.",
        )
        return
    yield AuditFinding(
        check="google.client_packages",
        title=f"{len(found)} Google client package(s) installed",
        severity=Severity.WARN,
        detail="Detected: " + ", ".join(found),
        recommendation=(
            "Consider replacements: F-Droid + Aurora Store, Organic Maps, "
            "K-9 Mail / FairEmail, NewPipe / LibreTube, FlorisBoard / "
            "HeliBoard."
        ),
    )


def check_adb_tcp(_adb: Adb, facts: DeviceFacts) -> Iterable[AuditFinding]:
    port = facts.adb_tcp_port
    if port and port.strip() and port != "0":
        yield AuditFinding(
            check="adb.tcp",
            title="ADB-over-network is enabled",
            severity=Severity.HIGH,
            detail=(
                f"service.adb.tcp.port = {port!r}. The device is exposing "
                "ADB on the network. Anyone on the same network can attempt "
                "to connect."
            ),
            recommendation=(
                "Disable wireless ADB in Developer options unless you "
                "actively need it on a trusted network."
            ),
        )
    else:
        yield AuditFinding(
            check="adb.tcp",
            title="ADB-over-network is not enabled",
            severity=Severity.OK,
            detail="service.adb.tcp.port is unset.",
        )


def check_private_dns(adb: Adb, _facts: DeviceFacts) -> Iterable[AuditFinding]:
    mode = adb.shell("settings get global private_dns_mode").strip()
    specifier = adb.shell("settings get global private_dns_specifier").strip()
    if mode in ("", "null", "off"):
        yield AuditFinding(
            check="dns.private",
            title="Private DNS is off",
            severity=Severity.WARN,
            detail=(
                f"global private_dns_mode = {mode!r}. DNS lookups go to "
                "whatever the network hands you, in cleartext."
            ),
            recommendation=(
                "Set Private DNS to a hostname (DoT) like dns.quad9.net "
                "in Settings > Network > Private DNS."
            ),
        )
        return
    if mode == "opportunistic":
        yield AuditFinding(
            check="dns.private",
            title="Private DNS is opportunistic",
            severity=Severity.INFO,
            detail=(
                "Android will use DoT when the upstream resolver supports "
                "it, otherwise fall back to cleartext."
            ),
        )
        return
    if mode == "hostname":
        yield AuditFinding(
            check="dns.private",
            title="Private DNS is enforced (DoT)",
            severity=Severity.OK,
            detail=(
                f"global private_dns_mode = 'hostname', specifier = "
                f"{specifier or '(unset)'!r}."
            ),
        )
        return
    yield AuditFinding(
        check="dns.private",
        title=f"Private DNS in unknown mode {mode!r}",
        severity=Severity.INFO,
        detail="Unrecognised private_dns_mode value; not interpreting.",
    )


def check_screen_lock(adb: Adb, _facts: DeviceFacts) -> Iterable[AuditFinding]:
    # `lockscreen.disabled` true means no lock at all on many AOSP ROMs.
    raw = adb.shell("settings get secure lockscreen.disabled").strip()
    disabled = raw == "1"
    if disabled:
        yield AuditFinding(
            check="lockscreen.present",
            title="Screen lock is disabled",
            severity=Severity.HIGH,
            detail="settings secure lockscreen.disabled = 1.",
            recommendation=(
                "Set a PIN, password, or passphrase. Without a screen lock, "
                "device encryption keys at rest are weakened."
            ),
        )
    else:
        yield AuditFinding(
            check="lockscreen.present",
            title="Screen lock appears enabled",
            severity=Severity.OK,
            detail=f"settings secure lockscreen.disabled = {raw!r}.",
        )


CHECKS: tuple[CheckFn, ...] = (
    check_lineage_identity,
    check_gms,
    check_gsf,
    check_common_google_packages,
    check_adb_tcp,
    check_private_dns,
    check_screen_lock,
)


def run_audit(adb: Adb, facts: DeviceFacts) -> AuditReport:
    findings: list[AuditFinding] = []
    for check in CHECKS:
        findings.extend(check(adb, facts))
    return AuditReport(findings=tuple(findings))
