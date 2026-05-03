"""Manufacturer-aware bootloader unlock guidance text.

Each guide is a plain-text string, ready to print. Guides are honest about
what cannot be automated and surface every relevant tradeoff.
"""

from __future__ import annotations

from .models import Manufacturer

# ---------------------------------------------------------------------------
# Standard fastboot path — Google Pixel, OnePlus, Fairphone
# ---------------------------------------------------------------------------

_STANDARD_FASTBOOT = """\
Standard fastboot unlock flow
═════════════════════════════

This device uses a standard fastboot-based unlock. The process is
straightforward but ERASES ALL DATA on the device — back up first.

  Step 1  Enable Developer Options
          Settings → About phone → tap "Build number" 7 times
          You should see "You are now a developer!"

  Step 2  Enable OEM unlocking
          Settings → System → Developer options → OEM unlocking → ON
          If this toggle is greyed out, your carrier may have locked
          the bootloader permanently; check XDA for your device.

  Step 3  Reboot to bootloader
          adb reboot bootloader
          The screen should show the bootloader/fastboot splash.

  Step 4  Unlock the bootloader  ⚠  THIS WIPES ALL DATA
          fastboot flashing unlock
          Use the volume keys to navigate to "Unlock the bootloader"
          and press the Power key to confirm on the device screen.

  Step 5  Wait for the factory reset and reboot
          The device will wipe itself and restart. Go through the
          minimal Android setup, then re-enable Developer Options and
          USB debugging before running `flash run`.

  Tradeoff  The device will show an "unlocked bootloader" warning on
            every boot. Verified Boot is disabled while unlocked.
"""

# ---------------------------------------------------------------------------
# Motorola — standard fastboot + unlock key from Motorola's website
# ---------------------------------------------------------------------------

_MOTOROLA_FASTBOOT = """\
Motorola unlock flow
════════════════════

Motorola requires a device-specific unlock key from their portal before
you can run `fastboot oem unlock`. The key is free but requires a
Motorola/Google account and takes a few minutes to obtain.

  Step 1  Enable Developer Options
          Settings → About phone → tap "Build number" 7 times

  Step 2  Enable OEM unlocking
          Settings → System → Developer options → OEM unlocking → ON
          (On some carriers this is permanently greyed out — if so,
          unlocking is not possible on that unit.)

  Step 3  Reboot to bootloader
          adb reboot bootloader

  Step 4  Retrieve your unlock data string
          fastboot oem get_unlock_data
          Copy the long hex string from the output (ignore newlines).

  Step 5  Request your unlock key
          Visit motorola.com/unlockbootloader, paste the unlock data,
          log in with your Google account, accept the terms, and wait
          for the email containing your unlock key.

  Step 6  Apply the unlock key  ⚠  THIS WIPES ALL DATA
          fastboot oem unlock <KEY_FROM_EMAIL>
          Replace <KEY_FROM_EMAIL> with the full string from the email.
          Confirm on the device when prompted.

  Step 7  Continue with the standard flash flow
          fastboot flash recovery recovery.img
          fastboot reboot recovery
          adb sideload lineage-*.zip

  Tradeoff  The unlock is tied to your Google account. If Motorola's
            portal is unavailable, you cannot unlock the device.
"""

# ---------------------------------------------------------------------------
# Samsung — Heimdall (open-source, cross-platform) + Odin fallback
# ---------------------------------------------------------------------------

_SAMSUNG_HEIMDALL = """\
Samsung flash flow via Heimdall (open-source, cross-platform)
═════════════════════════════════════════════════════════════

Samsung devices do not use standard fastboot. Heimdall is an open-source
replacement for Samsung's proprietary Odin tool. Install it first:
  • Arch/Manjaro:  sudo pacman -S heimdall-flash
  • Debian/Ubuntu: sudo apt install heimdall-flash
  • Fedora:        sudo dnf install heimdall
  • macOS:         brew install heimdall
  • Windows:       github.com/Benjamin-Dobell/Heimdall/releases

  Step 1  Enable Developer Options
          Settings → About phone → tap "Build number" 7 times

  Step 2  Enable OEM unlocking  ⚠  CRITICAL
          Settings → Developer options → OEM unlocking → ON
          If this toggle is greyed out, your carrier has locked the
          bootloader. Most carrier-locked Samsung devices cannot be
          flashed. Check XDA for your specific model.

  Step 3  Enter Download Mode
          Power the device off completely, then:
          • Devices WITH Home button (S7 and earlier):
            hold Vol Down + Home + Power simultaneously
          • Devices WITHOUT Home button (S8, S9, Note 8/9):
            hold Vol Down + Bixby + Power simultaneously
          • Newer devices (S10 and later, no Bixby button):
            hold Vol Down + Vol Up, then quickly connect USB cable
          The screen should show a warning triangle. Press Vol Up to
          accept and enter Download Mode.

  Step 4  Verify Heimdall can see the device
          heimdall detect
          (Linux: you may need to add udev rules. See
          wiki.lineageos.org/adb_fastboot_guide for the udev snippet.)

  Step 5  Flash the recovery partition  ⚠  THIS WIPES ALL DATA
          heimdall flash --RECOVERY recovery.img
          Wait for "Session ended successfully".

  Step 6  Boot into recovery IMMEDIATELY
          Do NOT let the device reboot normally — Samsung overwrites the
          custom recovery on the first normal Android boot.
          While Heimdall is still finishing (or immediately after):
          • S7 and earlier:  hold Vol Up + Home + Power
          • S8/S9/Note 8/9: hold Vol Up + Bixby + Power
          • S10 and later:   hold Vol Up + Power
          until the LineageOS recovery screen appears.

  Step 7  Sideload the ROM
          In recovery choose "Apply update" → "Apply from ADB", then:
          adb sideload lineage-*.zip

  Tradeoff  Samsung's Exynos variants often have closed bootloaders on
            certain regions/carriers. The process is less reliable than
            on Snapdragon variants. Always check XDA for your exact
            model number (SM-GXXX) before proceeding.
"""

_SAMSUNG_ODIN_FALLBACK = """\
Samsung flash flow via Odin (Windows-only, proprietary)
═══════════════════════════════════════════════════════

Odin is Samsung's official (closed-source, Windows-only) flashing tool.
Use Heimdall if possible; fall back to Odin only if Heimdall does not
work on your device or you are on Windows without WSL.

  Step 1  Download Odin
          Search for "Odin3 download" on odindownload.com or samfrew.com.
          Verify the SHA-256 of the downloaded binary before running it.
          Do NOT run arbitrary .exe files from unknown sources.

  Step 2  Enter Download Mode (same as Heimdall Step 3 above).

  Step 3  Open Odin as Administrator.
          The COM port field in Odin should light up green when the
          device in Download Mode is connected over USB.

  Step 4  Load the recovery image into the AP slot.
          Click "AP" in Odin and select your recovery.img.
          Leave BL, CP, and CSC slots EMPTY unless you know exactly
          what they do — flashing the wrong file there can brick the device.
          Uncheck "Auto Reboot" if the option is visible.

  Step 5  Click Start and wait for "PASS!" in Odin.

  Step 6  Boot into recovery IMMEDIATELY (same as Heimdall Step 6 above).
          If the device reboots to Android first, Samsung will replace
          the custom recovery with the stock one.

  Step 7  Sideload the ROM via ADB (same as Heimdall Step 7 above).
          adb sideload lineage-*.zip
"""

# ---------------------------------------------------------------------------
# Xiaomi / Redmi / POCO — Mi Unlock Tool (Windows, mandatory wait)
# ---------------------------------------------------------------------------

_XIAOMI_UNLOCK = """\
Xiaomi / Redmi / POCO unlock flow
══════════════════════════════════

Xiaomi enforces a mandatory server-side waiting period (7–30 days,
depending on your account age and region) between linking your Mi account
and being allowed to unlock. This cannot be bypassed. The official unlock
tool is also Windows-only. Plan accordingly.

  Step 1  Log into your Mi account on the device
          Settings → Mi Account (sign in if you haven't already)
          The account must stay linked until the waiting period elapses.

  Step 2  Enable Developer Options
          Settings → About phone → MIUI version → tap 7 times

  Step 3  Link Mi account to the bootloader unlock request
          Settings → Additional settings → Developer options →
          Mi Unlock status → "Add account and device"
          The device must be online (not on airplane mode) for this step.
          Note the date — the waiting clock starts now.

  Step 4  Wait 7–30 days
          Xiaomi enforces this server-side. Apps that claim to skip it
          do not work and may compromise your account. Do not unlink your
          Mi account during this period.

  Step 5  Download Mi Unlock Tool (Windows only)
          miui.com/unlock/download.html
          Run as Administrator. Log in with the same Mi account.

  Step 6  Reboot device to fastboot mode
          Power off completely → hold Power + Vol Down simultaneously

  Step 7  Connect device and click Unlock in Mi Unlock Tool
          If the tool reports "Waiting period not elapsed", it will show
          the remaining time. If it says "Unlocked successfully", the
          device wipes itself and reboots.

  Step 8  From here, standard fastboot commands work
          fastboot flash recovery recovery.img
          fastboot reboot recovery
          adb sideload lineage-*.zip

  Alternative  Some global Xiaomi variants also accept:
               fastboot flashing unlock
               Try this before the GUI tool — it may save you the wait
               on newer global firmware.

  Tradeoff  The waiting period is non-negotiable. Xiaomi account data
            is transmitted to Xiaomi servers during the link step.
            If you prefer not to create a Mi account, some community
            tools (e.g., mtkclient for MediaTek devices) exist but are
            outside the scope of this tool.
"""

# ---------------------------------------------------------------------------
# Generic fallback — unknown manufacturer
# ---------------------------------------------------------------------------

_GENERIC_FASTBOOT = """\
Generic fastboot unlock flow
════════════════════════════

This device's manufacturer was not specifically recognised. Standard
fastboot commands may work — check XDA Developers for your exact model.

  Step 1  Enable Developer Options
          Settings → About phone → tap "Build number" 7 times

  Step 2  Enable OEM unlocking
          Settings → System → Developer options → OEM unlocking → ON
          If greyed out, the bootloader may be permanently locked by
          the carrier or manufacturer.

  Step 3  Reboot to bootloader
          adb reboot bootloader

  Step 4  Unlock — try both commands; only one will work:
          fastboot flashing unlock       (most modern devices)
          fastboot oem unlock            (older devices, e.g. Nexus era)
          Confirm on the device screen if prompted.  ⚠  This wipes data.

  Step 5  Flash recovery and sideload the ROM
          fastboot flash recovery recovery.img
          fastboot reboot recovery
          adb sideload lineage-*.zip

  If these commands fail, search XDA Developers for your device model.
  The thread title usually follows the pattern:
    [ROM][LineageOS][<codename>] — this will have unlock instructions.
"""

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_GUIDES: dict[Manufacturer, str] = {
    Manufacturer.GOOGLE: _STANDARD_FASTBOOT,
    Manufacturer.ONEPLUS: _STANDARD_FASTBOOT,
    Manufacturer.FAIRPHONE: _STANDARD_FASTBOOT,
    Manufacturer.MOTOROLA: _MOTOROLA_FASTBOOT,
    Manufacturer.SAMSUNG: _SAMSUNG_HEIMDALL,
    Manufacturer.XIAOMI: _XIAOMI_UNLOCK,
    Manufacturer.GENERIC: _GENERIC_FASTBOOT,
}


def unlock_guide(manufacturer: Manufacturer) -> str:
    """Return the full unlock guide for the given manufacturer."""
    return _GUIDES.get(manufacturer, _GENERIC_FASTBOOT)


def samsung_odin_guide() -> str:
    """Return the Odin fallback guide for Samsung devices without Heimdall."""
    return _SAMSUNG_ODIN_FALLBACK
