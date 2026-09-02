"""Static pre-flash backup guidance (Phase 11).

``flash backup`` is read-only and requires no device connection: it
prints an honest checklist of what to back up before unlocking or
flashing, and what each destructive step wipes.
"""

from __future__ import annotations

_BACKUP_GUIDE = """\
Pre-flash backup guidance
=========================

Two steps in this workflow are destructive, and they wipe different
things. Know both before you start.

  Milestone 1  Bootloader unlock (flash prepare)
                  Factory-resets the entire device. Nothing survives —
                  apps, app data, photos, settings, accounts.
                  Back up first. There is no undo.

  Milestone 2  ROM flash (flash run)
                  Replaces the system partitions. Usually keeps user
                  data when you stay on the same major LineageOS
                  version; crossing major versions or flashing a
                  sister distro usually requires a full data wipe.
                  Settings and app state may reset partially either
                  way.

What to back up (before Milestone 1)
------------------------------------
  Photos/videos   Google Photos (or another cloud), or just
                  `adb pull /sdcard` / copy over MTP.
  SMS / MMS       per-app export (e.g. SMS Backup & Restore) —
                  `adb backup` is not reliable for this.
  Chat history    per-app export (Signal / Telegram / WhatsApp).
                  Signal's export is a .db file — attachments are NOT
                  in it; copy /sdcard separately.
  Documents       /sdcard/Download and /sdcard/Documents over
                  MTP or adb pull.
  Accounts        write down email addresses and passwords —
                  the device cannot back these up for you.
  Unlock flow     save this OEM's unlock procedure now; some are
                  time-limited or one-shot.

AOSP `adb backup` — how much to trust it
----------------------------------------
  - On modern AOSP-derived ROMs it is frequently disabled or
    produces empty/partial bundles.
  - It only picks up data from apps that explicitly opt in, a
    small minority.
  - Treat it as a bonus, not a backup. If it is the only backup
    you have, you don't have one.

Custom-recovery nandroid (TWRP / OrangeFox), if you already have
one
  - A nandroid is a full-disk image (system + data), restorable on
    the same ROM.
  - If your data is encrypted and the bootloader was locked when
    the capture was taken, unlocking changes the disk-encryption
    key — the old data image generally will not mount afterwards.
    File-level backups still survive.
  - In practice: keep the nandroid you have if it works; don't
    count on one you haven't tested.

Manufacturer notes
------------------
  Samsung     EFS holds modem configuration (IMEI, bands) and
              fingerprint data. Some heimdall operations can wipe
              it. If you go the `heimdall` route, dump EFS first:
              `heimdall print-pit` to find the partition name, then
              `heimdall dump --partition EFS --output efs.img`.
              Do this before anything destructive.
  Xiaomi      Mi Unlock requires account binding plus a wait time
              before it will work; some recent models do not allow
              bootloader unlock at all — check before you plan.
              Unlocking wipes everything, like Milestone 1.
  Pixel       standard fastboot unlock; the wipe is Milestone 1,
              nothing exotic. Verified Boot is disabled while
              unlocked — expected, not a failure.
  Others      if the OEM unlocking toggle is greyed out, the
              bootloader may be permanently locked (carrier or
              region); check XDA for your device before investing
              time.

After first boot
----------------
Once the new ROM is booted and setup is done:

  los-bootstrap flash check    did the install land cleanly?
  los-bootstrap audit          privacy posture of the new system
  los-bootstrap harden         read-only lockdown report

A `flash check` exit code of 3 means a check actually failed — read
the report before you start moving your data back. Warnings and checks
that could not be completed are printed too, without failing the
command.
"""


def backup_guide() -> str:
    """Return the static pre-flash backup checklist."""
    return _BACKUP_GUIDE
