"""Extended contextual prose for audit and harden findings.

Each FindingProse is keyed by check_id and used by wizard screens and
--verbose rendering to give users richer "what does this mean for me?"
explanations beyond the terse inline fields.

No imports beyond dataclasses — pure data, no IO, no ADB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FindingProse:
    check_id: str
    what: str
    why: str
    fix: str
    tradeoff: str
    common_causes: Optional[str] = None


# ── Audit findings ────────────────────────────────────────────────────────────

_AUDIT_PROSE: list[FindingProse] = [
    FindingProse(
        check_id="rom.lineage",
        what=(
            "This check detects whether the ROM is LineageOS by reading the "
            "ro.lineage.version system property."
        ),
        why=(
            "los-bootstrap gives device-specific guidance based on LineageOS "
            "conventions. On AOSP-derived ROMs the tool still works, but some "
            "paths (e.g. harden toggle locations) may differ slightly."
        ),
        fix="No action needed — this is informational.",
        tradeoff="N/A.",
        common_causes=(
            "Not LineageOS? Other AOSP derivatives (CalyxOS, GrapheneOS, "
            "DivestOS, /e/OS) do not set ro.lineage.version. The rest of the "
            "audit still applies."
        ),
    ),
    FindingProse(
        check_id="gms.present",
        what=(
            "Google Mobile Services (GMS) — package com.google.android.gms — "
            "was detected on the device. GMS is the proprietary Google layer "
            "that powers push notifications, location, and app attestation for "
            "most Play Store apps."
        ),
        why=(
            "A truly degoogled ROM should not include GMS. Its presence means "
            "Google can collect device telemetry, app-usage patterns, and "
            "location data even if you never open a Google app. GMS also "
            "communicates with Google servers in the background."
        ),
        fix=(
            "1. Run: adb shell pm path com.google.android.gms\n"
            "2. If the path starts with /system/app or /system/priv-app, "
            "real GApps were flashed. Reflash a vanilla LineageOS build.\n"
            "3. If the path is under /data/app, this is likely microG — "
            "a free-software GMS replacement. That is intentional and safe."
        ),
        tradeoff=(
            "Removing real GMS breaks every app that depends on it: Play "
            "Store, Google Pay, banking apps with Play Integrity checks, and "
            "anything using Firebase Cloud Messaging for push. Replacing with "
            "microG restores partial compatibility."
        ),
        common_causes=(
            "Two common causes:\n"
            "1. A GApps package was flashed alongside LineageOS (e.g. "
            "BiTGApps, MindTheGApps, NikGApps).\n"
            "2. microG GmsCore is installed as an intentional GMS replacement "
            "on a microG-enabled ROM (e.g. LineageOS for microG)."
        ),
    ),
    FindingProse(
        check_id="gsf.present",
        what=(
            "Google Services Framework (GSF) — package com.google.android.gsf "
            "— was found. GSF is a lower-level dependency layer that GMS and "
            "many Google apps rely on for registration IDs and account tokens."
        ),
        why=(
            "GSF registers the device with Google servers on first boot and "
            "assigns a persistent device ID used across all Google services. "
            "Its presence strongly implies real GMS was flashed."
        ),
        fix="Same as GMS: investigate the APK path and reflash if unintended.",
        tradeoff="Same as GMS removal — app compatibility breaks without a replacement.",
    ),
    FindingProse(
        check_id="google.client_packages",
        what=(
            "One or more Google client apps were detected: Play Store, Google "
            "Maps, Gmail, YouTube, or Gboard."
        ),
        why=(
            "Each Google client app connects to Google's servers and may "
            "collect usage data, location, or contacts. On a degoogled setup "
            "these are typically replaced with open-source alternatives."
        ),
        fix=(
            "Remove or replace each app:\n"
            "• Play Store → F-Droid + Aurora Store (anonymous APK downloads)\n"
            "• Google Maps → Organic Maps or OsmAnd (offline OSM)\n"
            "• Gmail → K-9 Mail or FairEmail (open source, any IMAP/SMTP)\n"
            "• YouTube → NewPipe or LibreTube (no account required)\n"
            "• Gboard → FlorisBoard or HeliBoard (no telemetry)"
        ),
        tradeoff=(
            "Replacements may lack some convenience features. Aurora Store "
            "anonymous sessions occasionally fail; having a throwaway Google "
            "account improves reliability."
        ),
    ),
    FindingProse(
        check_id="adb.tcp",
        what=(
            "ADB-over-network (wireless ADB) is enabled. The device is "
            "listening for ADB connections on the local network, typically on "
            "TCP port 5555."
        ),
        why=(
            "ADB grants full shell access — equivalent to root on many ROMs. "
            "Any device on the same Wi-Fi network, or anyone who can reach "
            "the device's IP, can attempt to connect. Even with an "
            "authorisation prompt, a misconfigured or already-trusted host "
            "could connect silently."
        ),
        fix=(
            "Disable in Settings › Developer options › Wireless debugging "
            "(or 'ADB over network' depending on ROM version). "
            "Only re-enable on a trusted network when you need it."
        ),
        tradeoff=(
            "You lose the convenience of wireless adb. Reconnect via USB "
            "and re-enable wireless ADB only for the duration of the task."
        ),
    ),
    FindingProse(
        check_id="dns.private",
        what=(
            "Android's Private DNS setting controls whether DNS queries use "
            "DNS-over-TLS (DoT). It is currently off or not set."
        ),
        why=(
            "Without DoT, every domain lookup travels over the network in "
            "cleartext UDP. Even when every website you visit uses HTTPS, "
            "the domain names themselves — signal.org, proton.me — are "
            "visible to your ISP, the Wi-Fi router operator, and any passive "
            "observer on the path. This matters extra on a degoogled ROM: "
            "you have already limited what Google sees; leaving DNS cleartext "
            "hands the same data to your network provider."
        ),
        fix=(
            "1. Open Settings › Network & Internet › Private DNS.\n"
            "2. Choose 'Private DNS provider hostname'.\n"
            "3. Enter dns.quad9.net (privacy-focused, blocks malicious domains)\n"
            "   or 1dot1dot1dot1.cloudflare-dns.com (fast, minimal logging).\n"
            "4. Tap Save."
        ),
        tradeoff=(
            "You are trusting the DNS provider instead of your ISP. Both can "
            "see query domain names; choose one you trust. Some captive portals "
            "(hotel/airport Wi-Fi) break with enforced DoT — switch to "
            "'Automatic' temporarily on those networks."
        ),
    ),
    FindingProse(
        check_id="lockscreen.present",
        what=(
            "The screen lock is disabled. The device will not prompt for a "
            "PIN, password, or biometric when woken."
        ),
        why=(
            "Android's file-based encryption (FBE) ties the encryption keys "
            "to the user's credential. Without a screen lock credential, those "
            "keys are derived from a device-internal value only — not something "
            "the attacker doesn't already have. Physical access to the powered-on "
            "device gives full data access."
        ),
        fix=(
            "Settings › Security › Screen lock. Choose PIN (minimum), "
            "password (better), or passphrase (best). Swipe-only counts as "
            "no lock for encryption purposes."
        ),
        tradeoff=(
            "You must authenticate every time you wake the device. Fingerprint "
            "or face unlock reduces friction but is subject to compelled-unlock "
            "in some jurisdictions."
        ),
    ),
]

# ── Harden findings ───────────────────────────────────────────────────────────

_HARDEN_PROSE: list[FindingProse] = [
    FindingProse(
        check_id="dev.options",
        what=(
            "Developer options are enabled system-wide. This unlocks a menu "
            "of debugging tools that are not intended for everyday use."
        ),
        why=(
            "The Developer options menu exposes: mock location providers "
            "(GPS spoofing), layout inspection tools, background process limits, "
            "USB debugging toggle, and more. These expand the attack surface "
            "beyond what a typical user needs after setup."
        ),
        fix=(
            "Open Settings › Developer options and toggle the master switch off. "
            "(On some ROMs it is listed as 'Developer mode'.)"
        ),
        tradeoff=(
            "Disabling Developer options hides the USB debugging toggle. "
            "You can re-enable the whole menu at any time by tapping Build "
            "number seven times in Settings › About phone."
        ),
    ),
    FindingProse(
        check_id="dev.adb",
        what=(
            "USB debugging (ADB) is enabled. The device will accept ADB "
            "commands over USB from any host the user authorises."
        ),
        why=(
            "ADB provides a shell with broad system access — install APKs, "
            "read app data, change settings, and more. Once a host is "
            "authorised, it retains that trust persistently. Leaving ADB "
            "on after initial setup is unnecessary and increases risk from "
            "physical USB access (e.g. a malicious charging cable or kiosk)."
        ),
        fix="Settings › Developer options › USB debugging → off.",
        tradeoff=(
            "You cannot run adb commands or sideload APKs until USB debugging "
            "is re-enabled. Re-enable it only when you need it, then turn it "
            "off again."
        ),
    ),
    FindingProse(
        check_id="sec.screen_lock",
        what="The screen lock credential is disabled (see audit finding for full detail).",
        why=(
            "Without a screen lock, Android's encryption key derivation does "
            "not depend on a secret the attacker lacks. Physical access to the "
            "powered-on device is equivalent to full data access."
        ),
        fix=(
            "Settings › Security › Screen lock — choose PIN, password, or "
            "passphrase. Avoid 'None' or 'Swipe'."
        ),
        tradeoff=(
            "Every wake-from-sleep requires authentication. Fingerprint/face "
            "reduces friction but may be subject to legal compelled-unlock."
        ),
    ),
    FindingProse(
        check_id="sec.encryption",
        what=(
            "This check reads ro.crypto.state and ro.crypto.type to determine "
            "whether on-device storage is encrypted."
        ),
        why=(
            "Encryption protects your data if the device is lost, stolen, or "
            "seized. Without it, pulling the storage (or booting a custom "
            "recovery) gives plain-text access to all user data."
        ),
        fix=(
            "On Android 10+, storage should always be encrypted. If yours is "
            "not, the ROM build may be non-standard. A factory reset followed "
            "by a clean LineageOS flash typically resolves this."
        ),
        tradeoff=(
            "No meaningful performance tradeoff on modern hardware. "
            "Decryption is transparent and hardware-accelerated."
        ),
    ),
    FindingProse(
        check_id="sec.unknown_sources",
        what=(
            "The legacy 'Install from unknown sources' global flag is enabled. "
            "This pre-Android-8 setting allowed APK installs from any source "
            "system-wide."
        ),
        why=(
            "Leaving this flag set signals that at some point the device was "
            "opened to unrestricted APK installs. On Android 8+, per-app "
            "install permissions are more granular, but the legacy flag "
            "remaining at '1' is still a hygiene concern worth clearing."
        ),
        fix=(
            "Clear the legacy flag:\n"
            "  adb shell settings put secure install_non_market_apps 0\n\n"
            "Also review per-app install permissions:\n"
            "  Settings › Apps › Special app access › Install unknown apps"
        ),
        tradeoff=(
            "Clearing the global flag does not revoke per-app install "
            "permissions already granted (e.g. F-Droid, Aurora Store). "
            "Those apps continue to install APKs normally."
        ),
    ),
    FindingProse(
        check_id="sec.verified_boot",
        what=(
            "Verified Boot (Android Verified Boot 2 / AVB) checks the "
            "cryptographic signature of the boot and system images at every "
            "boot. The state is read from ro.boot.verifiedbootstate."
        ),
        why=(
            "An unlocked bootloader (orange state) means anyone with physical "
            "access can replace the OS without triggering a warning. The device "
            "will still boot, but integrity is not guaranteed. A red state "
            "means verification has already failed."
        ),
        fix=(
            "Orange state: re-lock via 'fastboot oem lock' or "
            "'fastboot flashing lock' (device-specific). Only do this if your "
            "ROM explicitly supports re-locking — consult the LineageOS wiki "
            "for your device.\n\n"
            "Red state: investigate immediately; the OS may be compromised."
        ),
        tradeoff=(
            "Re-locking requires a ROM that ships with its own AVB signing "
            "key. Getting this wrong can brick the device. Read your ROM's "
            "documentation carefully before locking."
        ),
    ),
    FindingProse(
        check_id="sec.lockdown_menu",
        what=(
            "The Lockdown option is not present in the power menu. Lockdown "
            "is a single-tap emergency that immediately disables fingerprint, "
            "face unlock, and Smart Lock."
        ),
        why=(
            "If you face a situation where you must hand over the device — "
            "border crossing, arrest, theft — Lockdown lets you disable "
            "biometric unlock in one press before handing it over. After "
            "Lockdown, only the PIN or password can unlock the device."
        ),
        fix=(
            "Settings › Display or Security (depends on ROM) › "
            "'Show lockdown option'. Or apply via ADB:\n"
            "  adb shell settings put secure lockdown_mode_allowed 1"
        ),
        tradeoff=(
            "None. Lockdown does not wipe data. It only forces a credential "
            "unlock for the next session. You can always re-enable biometrics "
            "after unlocking normally."
        ),
    ),
    FindingProse(
        check_id="sec.selinux",
        what=(
            "SELinux (Security-Enhanced Linux) is read via 'getenforce' using "
            "root access. It can be in Enforcing, Permissive, or Disabled mode."
        ),
        why=(
            "SELinux Enforcing mode applies a mandatory access-control policy "
            "to every process. Even if an app is exploited, it cannot perform "
            "actions outside its policy domain. Permissive mode logs violations "
            "but never blocks them — it is essentially disabled from a security "
            "perspective."
        ),
        fix=(
            "Set SELinux to Enforcing immediately:\n"
            "  adb shell su -c setenforce 1\n\n"
            "This takes effect immediately but resets on reboot if the ROM "
            "boot script sets it back. Check /system/etc/selinux/ for "
            "persistent configuration."
        ),
        tradeoff=(
            "A small number of poorly written apps rely on policy violations "
            "to function. On stock LineageOS, no supported app should require "
            "Permissive mode."
        ),
    ),
]

# ── Public lookup ─────────────────────────────────────────────────────────────

FINDING_PROSE: dict[str, FindingProse] = {
    p.check_id: p for p in _AUDIT_PROSE + _HARDEN_PROSE
}


def get_prose(check_id: str) -> Optional[FindingProse]:
    return FINDING_PROSE.get(check_id)
