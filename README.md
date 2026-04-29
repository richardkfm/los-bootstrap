```
   ██╗      ██████╗ ███████╗  ╷  ╔╗ ╔═╗╔═╗╔╦╗╔═╗╔╦╗╦═╗╔═╗╔═╗
   ██║     ██╔═══██╗██╔════╝  │  ╠╩╗║ ║║ ║ ║ ╚═╗ ║ ╠╦╝╠═╣╠═╝
   ██║     ██║   ██║███████╗  │  ╚═╝╚═╝╚═╝ ╩ ╚═╝ ╩ ╩╚═╩ ╩╩
   ██║     ██║   ██║╚════██║  │   post-install · degoogled
   ███████╗╚██████╔╝███████║  │   adb-driven · audit-first
   ╚══════╝ ╚═════╝ ╚══════╝  ╵
```

[![CI](https://github.com/richardkfm/los-bootstrap/actions/workflows/ci.yml/badge.svg)](https://github.com/richardkfm/los-bootstrap/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.6.0-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android%20%2F%20LineageOS-brightgreen)](https://lineageos.org/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CLAUDE.md)

A CLI-first post-install assistant for **LineageOS** and other
AOSP-derived, degoogled Android ROMs. It does not flash ROMs. It helps
with everything that comes *after* you flash.

> **Status:** Phase 5 — Camera / GCam port profiles. Read-only by
> default; mutating commands (`apply`, `harden --interactive --confirm`)
> only run with explicit `--confirm`. See [`roadmap.md`](./roadmap.md)
> for what comes next.

## Why

Once LineageOS is installed, the next few hours are usually spent
sideloading F-Droid, fighting with maps/location, deciding whether to
add microG, and trying to remember which Google packages somehow ended
up on the device. `los-bootstrap` makes that part faster and more
honest:

- **Audit first.** See exactly what's on your device before changing it.
- **CLI over GUI.** Designed for the desktop terminal + `adb`.
- **Tradeoffs visible.** Recommendations come with downsides, not just
  upsides.
- **Pluggable.** Device-specific knowledge lives in YAML, not `if`-trees.

## Install

Requires Python 3.10+ and the `adb` binary on `$PATH`.

```bash
git clone <this-repo> los-bootstrap
cd los-bootstrap
pip install -e .
```

## Quick start

Plug in your phone, enable USB debugging, accept the RSA prompt, then:

```bash
los-bootstrap devices            # list connected devices
los-bootstrap info               # device, ROM, build, security patch
los-bootstrap audit              # privacy/degoogle audit
los-bootstrap report             # full report (info + audit)
los-bootstrap report --json      # machine-readable
los-bootstrap recommend          # non-binding bootstrap suggestions

los-bootstrap profiles list                       # list bundled profiles
los-bootstrap plan    --profile privacy-default   # dry-run a profile
los-bootstrap apply   --profile privacy-default --confirm

los-bootstrap harden                              # lockdown report with why + tradeoff
los-bootstrap harden --interactive                # walk through findings, show fix commands
los-bootstrap harden --interactive --confirm      # walk through and apply fixes via adb
los-bootstrap harden --root                       # add SELinux check (needs su access)

los-bootstrap location doctor                     # diagnose the location stack on device
los-bootstrap location compat                     # app location compatibility matrix

los-bootstrap camera list-profiles                # list known GCam port profiles
los-bootstrap camera show panther                 # full port details + XML config path
```

If you have more than one device connected, pass `--serial <id>`.
The `camera` and `location compat` commands need no device connection.

## What it currently does

### Audit (Phase 1)

- Detects connected devices via `adb devices`.
- Reads ROM identity from `getprop` (`ro.build.*`, `ro.product.*`,
  `ro.lineage.*` when present).
- Runs a privacy audit:
  - Google Mobile Services (`com.google.android.gms`) presence
  - Google Services Framework (`com.google.android.gsf`) presence
  - Common Google client packages (Maps, Play Store, GBoard, etc.)
  - ADB-over-network (`service.adb.tcp.port`) state
  - Private DNS (DoT) configuration
  - Screen lock configuration
- Renders findings as a human-readable report (or JSON).
- Suggests bootstrap actions — without applying them.

### Bootstrap profiles (Phase 2)

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

### Hardening assistant (Phase 3)

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

### Location stack (Phase 4)

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

### Camera / GCam port profiles (Phase 5)

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

**Device not listed?** GCam ports are matched by SoC, not device name.
Run `adb shell getprop ro.board.platform` to find your chip, then look
for a matching build on celsoazevedo.com or your device's XDA thread.
`camera list-profiles` shows the full guidance.

#### Sideloading LMC 8.4

GCam APKs are proprietary — they are never auto-fetched by this tool.
To install via the `camera` bootstrap profile:

```bash
# 1. Download LMC 8.4 for your SoC from celsoazevedo.com
# 2. Rename it to lmc84.apk and place it in ~/los-apks/
los-bootstrap apply --profile camera --apk-dir ~/los-apks --confirm

# 3. Push the XML config (get the exact command from camera show)
los-bootstrap camera show <your-codename>
```

## What it does NOT do

- It does not flash anything.
- It does not auto-distribute GCam APKs or other proprietary binaries.
- Root is opt-in (`harden --root`) and only used to read SELinux state.
- It does not verify APK signatures — verify downloads out-of-band
  for security-critical installs (F-Droid, ReVanced Manager).

These and future plans are tracked in [`roadmap.md`](./roadmap.md).

## Project layout

See [`CLAUDE.md`](./CLAUDE.md) for the architecture, coding workflow,
versioning policy, and roadmap discipline rules.

## License

GPL-3.0. See `LICENSE`.
