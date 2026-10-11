"""Device-integrity diagnostics: the signals apps inspect before refusing to run.

Each finding explains which kinds of apps a signal tends to break, how to
change it, and what changing it costs. The doctor cannot obtain a real Play
Integrity verdict (that needs GMS and an app registered with Google Play),
so it reports the inputs to that verdict and says so plainly.

All checks are read-only. Root-only checks run only when `--root` is passed.
"""

from __future__ import annotations

from typing import Callable, Iterable

from ..adb import Adb, AdbCommandError
from ..device import DeviceFacts
from ..gms import GMS_MICROG, GMS_NONE, GMS_REAL, classify_gms_variant
from .models import IntegrityFinding, IntegrityReport, IntegrityStatus


IntegrityCheckFn = Callable[[Adb, DeviceFacts], Iterable[IntegrityFinding]]

PLAY_STORE_PACKAGE = "com.android.vending"

ROOT_MANAGER_PACKAGES: tuple[tuple[str, str], ...] = (
    ("com.topjohnwu.magisk", "Magisk"),
    ("me.weishu.kernelsu", "KernelSU"),
    ("me.bmax.apatch", "APatch"),
)


def _getprop(adb: Adb, key: str) -> str | None:
    try:
        return adb.getprop(key)
    except AdbCommandError:
        return None


def check_bootloader(adb: Adb, _facts: DeviceFacts) -> Iterable[IntegrityFinding]:
    """Report the bootloader / verified-boot state apps read via attestation."""
    flash_locked = _getprop(adb, "ro.boot.flash.locked")
    device_state = _getprop(adb, "ro.boot.vbmeta.device_state")
    boot_state = _getprop(adb, "ro.boot.verifiedbootstate")
    detail = (
        f"ro.boot.flash.locked={flash_locked!r}, "
        f"ro.boot.vbmeta.device_state={device_state!r}, "
        f"ro.boot.verifiedbootstate={boot_state!r}"
    )
    why = (
        "Hardware-backed attestation reports the bootloader state directly "
        "from the phone's security chip. Apps that require the strongest "
        "integrity verdict — health-insurer ePA apps say so explicitly — "
        "exclude devices with an unlocked bootloader. A software module "
        "cannot change what the chip reports."
    )
    tradeoff = (
        "Relocking is only safe on ROMs that support it with their own "
        "signing key (e.g. GrapheneOS on Pixels, some CalyxOS and /e/OS "
        "devices). Relocking with an unsupported ROM can leave the phone "
        "unbootable, and the relock itself wipes all data."
    )
    if flash_locked == "0" or device_state == "unlocked" or boot_state == "orange":
        yield IntegrityFinding(
            check_id="int.bootloader",
            title="Bootloader unlocked",
            status=IntegrityStatus.WARN,
            detail=detail,
            why=why,
            tradeoff=tradeoff,
            fix_hint=(
                "Usually expected on LineageOS. Keep it unlocked unless your "
                "ROM documents a relock procedure for your exact device. See "
                "`los-bootstrap integrity guide` for alternatives."
            ),
        )
        return
    if flash_locked == "1" or device_state == "locked":
        yield IntegrityFinding(
            check_id="int.bootloader",
            title="Bootloader locked",
            status=IntegrityStatus.PASS,
            detail=detail,
            why=why,
            tradeoff="None.",
            fix_hint="",
        )
        return
    yield IntegrityFinding(
        check_id="int.bootloader",
        title="Bootloader state: could not be determined",
        status=IntegrityStatus.UNKNOWN,
        detail=detail,
        why=why,
        tradeoff="N/A",
        fix_hint="Check with `fastboot getvar unlocked` from the bootloader screen.",
    )


def check_build_keys(adb: Adb, _facts: DeviceFacts) -> Iterable[IntegrityFinding]:
    """Report whether the build is signed with public test keys."""
    tags = _getprop(adb, "ro.build.tags")
    if tags is None:
        yield IntegrityFinding(
            check_id="int.build_keys",
            title="Build signing: could not read ro.build.tags",
            status=IntegrityStatus.UNKNOWN,
            detail="getprop ro.build.tags failed.",
            why="",
            tradeoff="N/A",
            fix_hint="Inspect manually: adb shell getprop ro.build.tags",
        )
        return
    test_keys = "test-keys" in tags
    why = (
        "`release-keys` means the build was signed with a private key kept "
        "by the ROM maker; `test-keys` means it was signed with the public "
        "AOSP key anyone can use. Some apps treat a test-keys build as "
        "untrusted on its own."
    )
    yield IntegrityFinding(
        check_id="int.build_keys",
        title="Build signed with " + ("public test-keys" if test_keys else "release-keys"),
        status=IntegrityStatus.WARN if test_keys else IntegrityStatus.INFO,
        detail=f"ro.build.tags={tags!r}",
        why=why,
        tradeoff=(
            "A self-built or unofficial LineageOS image is usually test-keys; "
            "official signed builds are release-keys. Rebuilding with your own "
            "private keys removes this signal but does not affect the "
            "bootloader or attestation state."
            if test_keys
            else "None."
        ),
        fix_hint=(
            "Install an officially signed build, or sign your own build with a "
            "private key, if an app rejects test-keys."
            if test_keys
            else ""
        ),
    )


def check_gms(adb: Adb, _facts: DeviceFacts) -> Iterable[IntegrityFinding]:
    """Report the GMS variant and whether the Play Store is present."""
    variant = classify_gms_variant(adb)
    play_store = adb.package_installed(PLAY_STORE_PACKAGE)
    why = (
        "The Play Integrity API runs inside Google Play services and is "
        "requested through the Play Store. Without them an app that depends "
        "on a Play Integrity verdict cannot get one and typically refuses to "
        "start. microG answers many GMS API calls but does not produce a real "
        "Play Integrity verdict, so integrity-gated apps still fail."
    )
    if variant == GMS_NONE:
        status, title = IntegrityStatus.INFO, "No Google Play services (fully degoogled)"
        detail = "com.google.android.gms not installed; Play Store " + (
            "present" if play_store else "absent"
        )
    elif variant == GMS_MICROG:
        status, title = IntegrityStatus.INFO, "microG present (no real Play Integrity verdict)"
        detail = "com.google.android.gms is microG (versionName 0.x)"
    elif variant == GMS_REAL:
        status, title = IntegrityStatus.INFO, "Real Google Play services present"
        detail = "com.google.android.gms is real Play services; Play Store " + (
            "present" if play_store else "absent"
        )
    else:
        status, title = IntegrityStatus.UNKNOWN, "GMS present but variant unclear"
        detail = "com.google.android.gms installed; versionName unreadable"
    yield IntegrityFinding(
        check_id="int.gms",
        title=title,
        status=status,
        detail=detail,
        why=why,
        tradeoff=(
            "Real Play services restore the Play Integrity path but reintroduce "
            "the Google telemetry a degoogled ROM removed. microG is the "
            "middle ground for apps that only need GMS APIs, not a verdict."
        ),
        fix_hint=(
            "An app that only needs GMS APIs (maps, push) may work with microG; "
            "one that checks a Play Integrity verdict will not. Use "
            "`los-bootstrap integrity compat` to tell which is which."
        ),
    )


def check_adb_exposure(adb: Adb, _facts: DeviceFacts) -> Iterable[IntegrityFinding]:
    """Report developer-facing toggles some apps refuse to run alongside."""
    try:
        dev_opts = adb.shell("settings get global development_settings_enabled").strip()
    except AdbCommandError:
        dev_opts = ""
    try:
        adb_enabled = adb.shell("settings get global adb_enabled").strip()
    except AdbCommandError:
        adb_enabled = ""
    on = dev_opts == "1"
    yield IntegrityFinding(
        check_id="int.dev_options",
        title="Developer options " + ("enabled" if on else "disabled"),
        status=IntegrityStatus.WARN if on else IntegrityStatus.PASS,
        detail=f"development_settings_enabled={dev_opts!r}, adb_enabled={adb_enabled!r}",
        why=(
            "Several German banking apps refuse to start, or warn, while "
            "Developer options or USB debugging are enabled. This is a local "
            "setting an app can read directly — no attestation involved — so "
            "turning it off is the cheapest thing to try first."
        ),
        tradeoff=(
            "Turning Developer options off also hides the USB debugging "
            "toggle, so you will re-enable it before the next `adb` session."
            if on
            else "None."
        ),
        fix_hint=(
            "Settings > System > Developer options — toggle off."
            if on
            else ""
        ),
    )


def check_root(adb: Adb, _facts: DeviceFacts) -> Iterable[IntegrityFinding]:
    """Root-only: report installed root managers so spoofing modules are visible."""
    found: list[str] = []
    for package, label in ROOT_MANAGER_PACKAGES:
        try:
            if adb.package_installed(package):
                found.append(label)
        except AdbCommandError:
            continue
    yield IntegrityFinding(
        check_id="int.root",
        title=(
            "Root manager detected: " + ", ".join(found)
            if found
            else "No root manager detected"
        ),
        status=IntegrityStatus.INFO,
        detail="installed root managers: " + (", ".join(found) if found else "none"),
        why=(
            "A Magisk / KernelSU / APatch manager indicates the device is "
            "rooted, which is the prerequisite for installing a spoofing "
            "module. Many apps also detect root itself and refuse to run; "
            "those modules include a hide feature to suppress that signal."
        ),
        tradeoff=(
            "Root and third-party modules run with full privileges. Every "
            "module you add is code trusted with everything on the phone. Root "
            "does not make the device safer; it widens the attack surface."
        ),
        fix_hint=(
            "To install a spoofing module, see `los-bootstrap integrity guide`."
            if found
            else "Root is not required for the read-only checks above."
        ),
    )


READ_ONLY_CHECKS: tuple[IntegrityCheckFn, ...] = (
    check_bootloader,
    check_build_keys,
    check_gms,
    check_adb_exposure,
)

ROOT_CHECKS: tuple[IntegrityCheckFn, ...] = (check_root,)


def run_integrity_doctor(adb: Adb, facts: DeviceFacts, root: bool = False) -> IntegrityReport:
    checks = READ_ONLY_CHECKS + (ROOT_CHECKS if root else ())
    findings: list[IntegrityFinding] = []
    for check in checks:
        findings.extend(check(adb, facts))
    return IntegrityReport(findings=tuple(findings))
