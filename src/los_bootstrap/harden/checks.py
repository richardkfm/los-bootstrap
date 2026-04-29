"""Hardening checks — read-only ADB queries with rationale and tradeoffs.

Every check must document *why* the toggle matters and *what the user gives up*
by hardening it. "A recommendation without a downside is a bug." (CLAUDE.md)

Checks without `--root` use only `adb shell settings get` / `getprop`.
Root-only checks use `adb shell su -c <cmd>` and are gated behind `--root`.
"""

from __future__ import annotations

from typing import Callable, Iterable

from ..adb import Adb, AdbCommandError
from ..device import DeviceFacts
from .models import HardenFinding, HardenReport, HardenStatus


HardenCheckFn = Callable[[Adb, DeviceFacts], Iterable[HardenFinding]]


def check_developer_options(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    raw = adb.shell("settings get global development_settings_enabled").strip()
    enabled = raw == "1"
    yield HardenFinding(
        check_id="dev.options",
        title="Developer options " + ("enabled" if enabled else "disabled"),
        status=HardenStatus.WARN if enabled else HardenStatus.PASS,
        detail=f"settings global development_settings_enabled = {raw!r}",
        why=(
            "Developer options surface debugging and testing features that "
            "are unnecessary during daily use and expand the attack surface "
            "(e.g. mock locations, layout bounds, background process limits)."
        ),
        tradeoff=(
            "USB debugging (ADB) lives under Developer options. Disabling "
            "it means you can no longer sideload APKs or run adb commands "
            "until you re-enable the menu."
        ),
        fix_hint=(
            "Settings > About phone > tap Build number seven times, then "
            "open Developer options and toggle the master switch off."
        ),
        fix_command=None,  # no reliable settings-put path; must use UI
    )


def check_adb_enabled(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    raw = adb.shell("settings get global adb_enabled").strip()
    enabled = raw == "1"
    yield HardenFinding(
        check_id="dev.adb",
        title="USB debugging (ADB) " + ("enabled" if enabled else "disabled"),
        status=HardenStatus.WARN if enabled else HardenStatus.PASS,
        detail=f"settings global adb_enabled = {raw!r}",
        why=(
            "ADB grants arbitrary shell access and file transfer to anyone "
            "with physical USB access and a trusted host key. Leaving it on "
            "permanently is unnecessary once initial setup is complete."
        ),
        tradeoff=(
            "You will not be able to run adb commands or sideload APKs "
            "until USB debugging is re-enabled in Developer options."
        ),
        fix_hint="Settings > Developer options > USB debugging > off.",
        fix_command="settings put global adb_enabled 0",
    )


def check_screen_lock(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    raw = adb.shell("settings get secure lockscreen.disabled").strip()
    disabled = raw == "1"
    yield HardenFinding(
        check_id="sec.screen_lock",
        title="Screen lock " + ("disabled" if disabled else "appears enabled"),
        status=HardenStatus.FAIL if disabled else HardenStatus.PASS,
        detail=f"settings secure lockscreen.disabled = {raw!r}",
        why=(
            "Without a screen lock, Android's file-based encryption keys "
            "are not bound to a user credential. Physical access to the "
            "unlocked device grants full data access."
        ),
        tradeoff=(
            "You must unlock the device to use it. Biometric unlock "
            "(fingerprint / face) reduces friction but adds its own "
            "threat model (compelled unlock)."
        ),
        fix_hint=(
            "Settings > Security > Screen lock — choose PIN, password, "
            "or passphrase. Avoid swipe-only or no-lock options."
        ),
        fix_command=None,  # setting a credential via ADB is intentionally unsupported
    )


def check_encryption(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    try:
        state = adb.shell("getprop ro.crypto.state").strip()
        crypto_type = adb.shell("getprop ro.crypto.type").strip()
    except AdbCommandError:
        yield HardenFinding(
            check_id="sec.encryption",
            title="Encryption state could not be determined",
            status=HardenStatus.UNKNOWN,
            detail="getprop ro.crypto.state failed.",
            why="Full-disk or file-based encryption protects data at rest.",
            tradeoff="No tradeoff — encryption is transparent on modern Android.",
            fix_hint="Check ro.crypto.state manually via adb shell getprop ro.crypto.state.",
        )
        return

    if state == "encrypted":
        enc_label = f"file-based (FBE)" if crypto_type == "file" else f"block-level (FDE)"
        yield HardenFinding(
            check_id="sec.encryption",
            title=f"Storage is encrypted ({enc_label})",
            status=HardenStatus.PASS,
            detail=f"ro.crypto.state = {state!r}, ro.crypto.type = {crypto_type!r}",
            why="Encryption protects user data if the device is lost or stolen.",
            tradeoff="No meaningful tradeoff on modern hardware; decryption is transparent.",
            fix_hint="",
        )
    elif state == "unencrypted":
        yield HardenFinding(
            check_id="sec.encryption",
            title="Storage is NOT encrypted",
            status=HardenStatus.FAIL,
            detail=f"ro.crypto.state = {state!r}",
            why=(
                "Unencrypted storage means all user data is readable from "
                "a custom recovery or by booting a different OS on the device."
            ),
            tradeoff="None. Encryption is mandatory on Android 10+ and has no user-visible cost.",
            fix_hint=(
                "This is unusual on Android 10+. Check your ROM build; "
                "a factory reset may be required to re-enable encryption."
            ),
        )
    elif state in ("unsupported", ""):
        yield HardenFinding(
            check_id="sec.encryption",
            title="Encryption unsupported or not reported",
            status=HardenStatus.INFO,
            detail=f"ro.crypto.state = {state!r}",
            why="Encryption state is device- or ROM-specific.",
            tradeoff="N/A",
            fix_hint="Verify with your ROM's documentation.",
        )
    else:
        yield HardenFinding(
            check_id="sec.encryption",
            title=f"Encryption in unknown state: {state!r}",
            status=HardenStatus.UNKNOWN,
            detail=f"ro.crypto.state = {state!r}",
            why="Encryption state is device- or ROM-specific.",
            tradeoff="N/A",
            fix_hint="Check ro.crypto.state manually.",
        )


def check_unknown_sources(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    # Global install_non_market_apps was the pre-Android-8 knob.
    # Android 8+ moved this to a per-app permission, but many ROMs still
    # expose the global setting; a value of "1" means it was ever enabled.
    raw = adb.shell("settings get secure install_non_market_apps").strip()
    enabled = raw == "1"
    yield HardenFinding(
        check_id="sec.unknown_sources",
        title="Unknown sources (global) " + ("enabled" if enabled else "not enabled"),
        status=HardenStatus.WARN if enabled else HardenStatus.PASS,
        detail=f"settings secure install_non_market_apps = {raw!r}",
        why=(
            "Allowing APK installs from unreviewed sources increases the "
            "risk of sideloading malware. On Android 8+ this is per-app, "
            "but leaving the legacy global flag on signals the device was "
            "opened to unknown sources at some point."
        ),
        tradeoff=(
            "Disabling this blocks APK installs from file managers and "
            "browsers that have not been individually granted the "
            "REQUEST_INSTALL_PACKAGES permission. F-Droid and Aurora "
            "manage their own per-app permission separately."
        ),
        fix_hint=(
            "Settings > Security > Install unknown apps — review and revoke "
            "per-app install permissions. The legacy global flag can be "
            "cleared with: adb shell settings put secure "
            "install_non_market_apps 0"
        ),
        fix_command="settings put secure install_non_market_apps 0",
    )


def check_verified_boot(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    try:
        state = adb.shell("getprop ro.boot.verifiedbootstate").strip()
    except AdbCommandError:
        yield HardenFinding(
            check_id="sec.verified_boot",
            title="Verified boot state could not be determined",
            status=HardenStatus.UNKNOWN,
            detail="getprop ro.boot.verifiedbootstate failed.",
            why="Verified boot ensures the OS has not been tampered with at rest.",
            tradeoff="N/A",
            fix_hint="Check ro.boot.verifiedbootstate manually.",
        )
        return

    STATUS_MAP = {
        "green": (HardenStatus.PASS, "Verified boot: green (official key, unmodified)"),
        "yellow": (HardenStatus.WARN, "Verified boot: yellow (custom signing key)"),
        "orange": (HardenStatus.WARN, "Verified boot: orange (bootloader unlocked)"),
        "red": (HardenStatus.FAIL, "Verified boot: red (verification failed)"),
    }
    status, title = STATUS_MAP.get(state, (HardenStatus.UNKNOWN, f"Verified boot: {state!r}"))

    details = {
        "green": "The bootloader is locked and the OS matches the official signing key.",
        "yellow": (
            "A custom AVB key is enrolled. The ROM is verified but not by the OEM. "
            "This is expected on ROMs like DivestOS that ship their own keys."
        ),
        "orange": (
            "The bootloader is unlocked. Anyone with physical access can replace the "
            "OS without triggering a boot warning. Data is still encrypted but the "
            "encryption key can be replaced on next boot."
        ),
        "red": "Boot verification failed. The OS image may have been tampered with.",
    }
    detail_text = details.get(state, f"ro.boot.verifiedbootstate = {state!r}")

    tradeoffs = {
        "green": "None.",
        "yellow": "Tradeoff accepted when enrolling a custom AVB key.",
        "orange": (
            "Re-locking the bootloader requires a ROM that supports it and "
            "risks a brick if the signing keys do not match. Consult your "
            "ROM's documentation before locking."
        ),
        "red": "Investigate immediately; do not use the device for sensitive data.",
    }

    yield HardenFinding(
        check_id="sec.verified_boot",
        title=title,
        status=status,
        detail=f"ro.boot.verifiedbootstate = {state!r}. {detail_text}",
        why=(
            "Verified boot (AVB) ensures the OS has not been tampered with "
            "between boots. An unlocked or red-state bootloader undermines "
            "the integrity guarantee even if encryption is enabled."
        ),
        tradeoff=tradeoffs.get(state, "N/A"),
        fix_hint=(
            "Re-lock via fastboot oem lock (device-specific). Only do this "
            "if your ROM explicitly supports re-locking with its signing key."
        )
        if state == "orange"
        else "",
    )


def check_lockdown_power_menu(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    # "Lockdown mode" adds an option to the power menu that immediately
    # disables biometric unlock and Smart Lock until the next PIN/password entry.
    # The setting is lineage-specific but also present in AOSP 9+.
    raw = adb.shell("settings get secure lockdown_mode_allowed").strip()
    allowed = raw == "1"
    yield HardenFinding(
        check_id="sec.lockdown_menu",
        title="Lockdown in power menu " + ("enabled" if allowed else "not enabled"),
        status=HardenStatus.PASS if allowed else HardenStatus.WARN,
        detail=f"settings secure lockdown_mode_allowed = {raw!r}",
        why=(
            "The Lockdown option in the power menu lets you instantly disable "
            "fingerprint, face unlock, and Smart Lock — useful if you expect "
            "a compelled-unlock situation (border crossing, arrest, theft)."
        ),
        tradeoff=(
            "None. Lockdown does not wipe the device; it only forces "
            "a PIN/password for the next unlock."
        ),
        fix_hint=(
            "Settings > Display (or Security, depending on ROM) > "
            "Show lockdown option. Or apply via ADB: "
            "adb shell settings put secure lockdown_mode_allowed 1"
        ),
        fix_command="settings put secure lockdown_mode_allowed 1",
    )


# --- Root-only checks --------------------------------------------------------

def check_selinux(adb: Adb, _facts: DeviceFacts) -> Iterable[HardenFinding]:
    """Requires root; call only when --root is passed."""
    try:
        raw = adb.shell("su -c getenforce").strip()
    except AdbCommandError:
        yield HardenFinding(
            check_id="sec.selinux",
            title="SELinux state could not be read (root unavailable?)",
            status=HardenStatus.UNKNOWN,
            detail="su -c getenforce failed.",
            why="SELinux enforcing mode confines processes and limits damage from exploits.",
            tradeoff="Permissive mode is sometimes set by developers; it should not persist.",
            fix_hint="Ensure adb root access is available and re-run with --root.",
        )
        return
    enforcing = raw.lower() == "enforcing"
    yield HardenFinding(
        check_id="sec.selinux",
        title=f"SELinux is {raw}",
        status=HardenStatus.PASS if enforcing else HardenStatus.FAIL,
        detail=f"getenforce = {raw!r}",
        why=(
            "SELinux in Enforcing mode confines every process to a policy, "
            "drastically limiting what a compromised app or service can do. "
            "Permissive mode logs but never blocks policy violations."
        ),
        tradeoff=(
            "Enforcing mode can break poorly-written apps that rely on "
            "policy violations. On stock LineageOS this should never matter."
        ),
        fix_hint="adb shell su -c setenforce 1  (takes effect immediately, resets on reboot).",
        fix_command="su -c setenforce 1",
    )


# --- Orchestrator ------------------------------------------------------------

CHECKS: tuple[HardenCheckFn, ...] = (
    check_developer_options,
    check_adb_enabled,
    check_screen_lock,
    check_encryption,
    check_unknown_sources,
    check_verified_boot,
    check_lockdown_power_menu,
)

ROOT_CHECKS: tuple[HardenCheckFn, ...] = (
    check_selinux,
)


def run_harden_checks(adb: Adb, facts: DeviceFacts, root: bool = False) -> HardenReport:
    findings: list[HardenFinding] = []
    for check in CHECKS:
        findings.extend(check(adb, facts))
    if root:
        for check in ROOT_CHECKS:
            findings.extend(check(adb, facts))
    return HardenReport(findings=tuple(findings))
