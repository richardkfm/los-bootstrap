# What los-bootstrap does

[← README](../README.md) · [Install](INSTALL.md) · [Usage](USAGE.md) · [Features](FEATURES.md)

Detailed reference for each mode, in the order you would typically use
them. For the command list, see [USAGE.md](USAGE.md).

## ROM flashing assistant (Phase 8)

The complete ROM-install path for your phone or tablet — unlock,
download, verify, and the actual fastboot flash:

```bash
los-bootstrap flash status    # detect device state + manufacturer
los-bootstrap flash prepare   # manufacturer-aware unlock guide
los-bootstrap flash download  # download links (+ --fetch to get the zip)
los-bootstrap flash verify    # validate ROM zip
los-bootstrap flash run       # execute the flash sequence
los-bootstrap flash backup    # pre-flash backup guidance (no device needed)
los-bootstrap flash check     # post-flash first-boot verification
los-bootstrap flash update    # is my installed LineageOS build current?
```

`flash status` detects whether your device is in normal ADB mode,
fastboot/bootloader mode, or recovery, and identifies the manufacturer
from `ro.product.manufacturer`.

`flash prepare` shows the full bootloader unlock walkthrough for your
specific device, plus live pre-checks (Developer Options enabled? OEM
unlocking enabled?) when the device is accessible via ADB:

| Manufacturer | Approach |
|---|---|
| Google Pixel, OnePlus, Fairphone | Standard `fastboot flashing unlock` |
| Motorola | Unlock key from motorola.com, then `fastboot oem unlock` |
| Samsung | Heimdall (open-source, cross-platform); Odin fallback guide |
| Xiaomi / Redmi / POCO | Mi Unlock Tool walkthrough (Windows, 7–30 day wait) |
| Unknown / generic | XDA-oriented generic fastboot guide |

`flash verify` extracts `pre-device` from the ROM's OTA metadata and
cross-checks it against the connected device codename — a wrong-device
catch before anything destructive runs.

`flash run` executes the sequence. It detects A/B vs A-only partition
layout (`fastboot getvar slot-count`) and adjusts accordingly. Every
destructive step is skipped without `--confirm`. `--dry-run` prints the
full command sequence without running any of it.

The lifecycle checks (Phase 11) close the loop around the flash:

`flash backup` prints honest pre-flash backup guidance — what
`adb backup` can and can't capture, nandroid caveats, what the unlock
and what the flash each wipe, and per-manufacturer notes (Samsung EFS,
Xiaomi, Pixel). No device needed.

`flash check` is the post-flash first-boot verification: LineageOS
detection (including /e/OS), build fingerprint, verified-boot state
(red is a failure — usually a ROM for the wrong device; yellow, a
bootloader relocked with the ROM's own key, passes), A/B slot, GMS presence,
and build type. It distinguishes microG from real Play Services, and
probes that could not be read are reported as unknown rather than
silently counted as clean. Exits 3 on a genuine failure; warnings are
printed but do not change the exit code.

`flash update` compares your installed build date against the latest
official LineageOS build **on your own major version** and tells you how
many days you are behind. A newer major version is reported separately,
with the data-wipe caveat, because it is not a routine update. Exits 3
when outdated. `--no-network` skips the API lookup; if the API is
unreachable the report is still printed (with a link to the download
page) rather than the command failing.

## Audit (Phase 1)

- Detects connected devices via `adb devices`.
- Reads ROM identity from `getprop` (`ro.build.*`, `ro.product.*`,
  `ro.lineage.*` when present). Detects form factor (phone vs tablet)
  from `ro.build.characteristics` and surfaces it in `los-bootstrap info`.
- Runs a privacy audit:
  - Google Mobile Services (`com.google.android.gms`) presence
  - Google Services Framework (`com.google.android.gsf`) presence
  - Common Google client packages (Maps, Play Store, GBoard, etc.)
  - ADB-over-network (`service.adb.tcp.port`) state
  - Private DNS (DoT) configuration
  - Screen lock configuration
- Renders findings as a human-readable report (or JSON).
- Suggests bootstrap actions — without applying them.

## Bootstrap profiles (Phase 2)

Builds and applies **profiles**: a YAML-described list of apps to
install and `settings put` toggles. Bundled profiles:

- `minimal` — F-Droid + Private DNS
- `privacy-default` — adds maps, contacts, a browser, and DoT
- `messaging-light` — Signal, Element, Telegram X
- `max-tools` — broadest non-Google bundle: store, browser, maps,
  messaging, contacts/calendar, mail, media, productivity, password
  manager, RSS/podcasts, and **ReVanced Manager** for ad-free YouTube
- `camera` — sideloads LMC 8.4 from a manually staged APK (see below)

APKs are downloaded automatically when `apply` runs:

| Source in profile | How it's fetched |
|---|---|
| `source: sideload` + `url: https://…` | Downloaded directly |
| `source: sideload` + `url: github://owner/repo` | Latest `.apk` release asset from GitHub |
| `source: fdroid` | Resolved via F-Droid API → downloaded from `f-droid.org/repo/` |
| `source: aurora` | Manual — Aurora Store handles Play Store apps |

Pass `--no-fetch` to disable downloads and revert to manual staging.

```bash
los-bootstrap plan  --profile privacy-default               # dry-run
los-bootstrap apply --profile privacy-default --confirm     # execute
los-bootstrap apply --profile privacy-default --apk-dir ~/los-apks --confirm
```

## Hardening assistant (Phase 3)

Runs lockdown checks and guides you through each one:

| Check | What it detects |
|---|---|
| `dev.options` | Developer options enabled |
| `dev.adb` | USB debugging (ADB) enabled |
| `sec.screen_lock` | Screen lock disabled |
| `sec.encryption` | Unencrypted storage |
| `sec.unknown_sources` | Global unknown-sources install flag |
| `sec.verified_boot` | Bootloader unlocked / verification failed |
| `sec.lockdown_menu` | Lockdown option absent from power menu |
| `sec.selinux` | SELinux permissive (`--root` only) |

Every finding explains *why* it matters and *what you give up* by
hardening it. `--interactive` walks through each WARN/FAIL one at a
time and offers to apply the fix; `--confirm` is required to execute.

## Location stack (Phase 4)

```bash
los-bootstrap location doctor   # diagnose the device's location stack
los-bootstrap location compat   # static app compatibility matrix
```

`location doctor` checks: location master switch, real GMS conflict
with microG, microG GmsCore install, signature-spoofing grant, and
which UnifiedNlp network-location backends are installed. Every finding
has a *why* and a *tradeoff*.

`location compat` shows a static matrix of 14 real-world apps
(OsmAnd, Telegram, Signal, WhatsApp, Firefox, Chromium, Uber, and more)
rated as `yes / gps-only / partial / no` on a degoogled ROM. No device
connection required.

## Device integrity & app compatibility (Phase 12)

```bash
los-bootstrap integrity doctor          # diagnose the signals apps check (read-only)
los-bootstrap integrity doctor --root   # also list installed root/spoofing managers
los-bootstrap integrity compat          # German gov/banking app matrix (no device)
los-bootstrap integrity guide           # alternatives-first workaround guidance
los-bootstrap integrity install --list  # known spoofing modules
los-bootstrap integrity install <mod.zip> --root --confirm   # install a module
los-bootstrap integrity install --fetch <name> --root --confirm  # fetch + install
```

Some government and banking apps refuse to run on a custom ROM. `integrity`
helps you understand why and what your honest options are.

`integrity doctor` reports the signals those apps inspect — bootloader /
verified-boot state, whether the build is signed with public test-keys,
GMS vs microG, and Developer options / USB debugging — each with its likely
app impact and a tradeoff. It **cannot** obtain a real Play Integrity verdict
itself (that needs Google Play services and an app registered with Google);
it says so and points you at an on-device checker for the actual verdict.

`integrity compat` is a static matrix of German apps (AusweisApp, the TK ePA
app, ElsterSmart, Sparkasse S-pushTAN, DB Navigator, VR SecureGo plus) with a
non-phone alternative and a `last_verified` date for each. Entries older than
six months are shown as unverified on purpose — stale compatibility data is
worse than none.

`integrity guide` lists the workarounds from lowest risk to highest: a
web/desktop route, microG, a second device, a ROM that can relock its
bootloader (e.g. GrapheneOS), rooting, and — as a last resort — Play Integrity
spoofing. Spoofing keeps a working phone in service instead of replacing it,
but it is honest about the cost: it always prints three warnings —
**fragility** (Google revokes spoofed fingerprints, so it can break
overnight), **liability shift** (bank/eID terms may put fraud liability on
you), and **root attack surface**. This tool never deals in attestation
keyboxes.

`integrity install` installs a fingerprint-spoofing Magisk/KernelSU/APatch
module on an **already-rooted** device — the one mutating command in this
mode. It is gated on both `--root` and `--confirm`; without `--confirm` it
previews the module's `module.prop`, its SHA-256, the detected root manager,
and the three warnings, then stops. It refuses any zip without a
`module.prop`. Give it a local module zip you downloaded, or `--fetch <name>`
to pull the latest release from a repo declared in the bundled registry
(`integrity install --list`). `--fetch` is the only part that touches the
network. The registry lists only fingerprint-spoofing modules — never
keybox/TrickyStore ones. This tool does not root your device; see
`integrity guide` for that.

## Camera / GCam port profiles (Phase 5)

```bash
los-bootstrap camera list-profiles      # table of known device profiles
los-bootstrap camera show <codename>    # full details + XML config path
```

No device connection required. Per-device profiles include:

- Which GCam port is recommended (LMC 8.4, BSG 9.3, etc.)
- Verified/unverified tag — only marked verified from real usage reports
- Source guidance: where to download the correct build for your SoC
- XML config path (`/sdcard/GCam/Config/`) and the exact `adb push`
  command to apply it

Currently profiled devices:

| Codename | Device | Port |
|---|---|---|
| `panther` | Google Pixel 7 | LMC 8.4 R17 |
| `oriole` | Google Pixel 6 | LMC 8.4 R17 |
| `sunny` | Xiaomi Redmi Note 10 | BSG 9.3.020 (+ LMC 8.4) |
| `lemonade` | OnePlus 9 | BSG 9.3.020 |
| `FP4` | Fairphone 4 | LMC 8.4 R17 |
| `renoir` | Xiaomi Mi 11 Lite 5G | LMC 8.4 R17 |
| `nabu` | Xiaomi Pad 5 *(tablet)* | LMC 8.4 R17 |
| `jupiter` | OnePlus Pad *(tablet)* | LMC 8.4 R17 |

**Device not listed?** GCam ports are matched by SoC, not device name.
Run `adb shell getprop ro.board.platform` to find your chip, then look
for a matching build on celsoazevedo.com or your device's XDA thread.
`camera list-profiles` shows the full guidance.

### Sideloading LMC 8.4

GCam APKs are proprietary — they are never auto-fetched by this tool.
To install via the `camera` bootstrap profile:

```bash
# 1. Download LMC 8.4 for your SoC from celsoazevedo.com
# 2. Rename it to lmc84.apk and place it in ~/los-apks/
los-bootstrap apply --profile camera --apk-dir ~/los-apks --confirm

# 3. Push the XML config (get the exact command from camera show)
los-bootstrap camera show <your-codename>
```

## Interactive wizard and enriched output (Phase 6)

Run `los-bootstrap` with no arguments to launch the guided wizard:

```
los-bootstrap                            (no args → wizard)
├── Audit                — privacy & degoogle status      [read-only]
│   └── Drill-down on a specific finding (full prose)
├── Harden               — security checks            [can apply changes]
│   ├── Read-only report
│   ├── Interactive walk-through (per-finding confirm)
│   └── Include root-only checks (SELinux)
├── Bootstrap            — install apps + apply settings [can apply changes]
│   ├── Pick a bundled profile (minimal | privacy-default | messaging-light | max-tools | camera)
│   ├── Or load a custom profile path
│   └── Plan → Apply (confirm gate)
├── Location
│   ├── Doctor — diagnose the location stack          [ADB required]
│   └── App compatibility matrix                      [no ADB needed]
├── Camera                                            [no ADB needed]
│   ├── List all known device GCam port profiles
│   └── Look up a specific device by codename
├── Flash                — bootloader unlock + ROM flashing [advanced]
│   ├── Bootloader unlock guidance for this device   [read-only]
│   ├── Download a ROM (LineageOS API + sister distros, optional fetch)
│   ├── Verify a ROM zip (zip integrity + OTA codename match)
│   └── Flash a ROM                          [destructive — two-step confirm]
└── Exit
```

Highlights:

- Detects your connected device and enters offline mode if none is found
- **Audit screen** — runs all checks and shows findings grouped into
  *issues to address* and *passing checks*, with word-wrapped prose
- **Drill-down** — select any finding for a full "what's happening / why
  it matters / how to fix it / tradeoff" explanation
- **Harden screen** — choose read-only report or interactive walk-through;
  per-finding confirmation before applying any fix
- **Bootstrap screen** — profile picker → plan review → apply with
  confirmation
- **Location / Camera screens** — same diagnostics as the subcommands
- **Flash screen** — bootloader unlock guidance, LineageOS download
  (with SHA-256 verification), ROM zip verify, and a destructive flash
  run gated by a two-step confirmation
- **Offline mode** — no ADB device? Camera, Location compat, and most
  Flash sub-screens still work

All finding renderers are also improved in standalone (non-wizard) mode:
findings are now grouped by severity, long prose is wrapped at 72 chars,
and `→ Fix:` / `⚠ Tradeoff:` labels replace the old flat field list.

```
  ✗  Location disabled
     Location must be on for GPS, network, and passive providers to
     function. With it off, every app requesting a location fix receives
     nothing, regardless of backends or microG installed.

     → Fix: Settings › Location › Use location — toggle on.
     ⚠  Tradeoff: Enabling location allows apps with location permission
        to request your position. Only individually granted apps receive
        results.
```

**Optional dependency:** install `questionary` for arrow-key menus:

```bash
pip install "los-bootstrap[wizard]"
```

Without it the wizard falls back to numbered `input()` prompts and works
everywhere.

## What it does NOT do

- It does not bypass bootloader verification or carrier locks — it calls
  official unlock APIs only.
- It only fetches ROMs you explicitly ask for, from publishers' own APIs.
  `flash download --fetch` pulls the latest LineageOS zip from
  `download.lineageos.org` and verifies the published SHA-256; everything
  else is a printed link.
- It does not automate Samsung Odin (closed-source, Windows-only) or
  Xiaomi's Mi Unlock Tool (proprietary, server-enforced). It guides you
  through those manually.
- It does not auto-distribute GCam APKs or other proprietary binaries, and
  it never ships, fetches, or explains how to obtain Play Integrity
  attestation keyboxes. `integrity install --fetch` lists only
  fingerprint-spoofing modules, pulled from their own repos.
- Root is opt-in. `harden --root` reads SELinux state; `integrity install`
  (`--root --confirm`) installs a spoofing module on an already-rooted
  device. This tool never roots the device for you.
- It does not verify APK signatures — verify downloads out-of-band
  for security-critical installs (F-Droid, ReVanced Manager).

These and future plans are tracked in [`roadmap.md`](../roadmap.md).
