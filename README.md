```
   ██╗      ██████╗ ███████╗  ╷  ╔╗ ╔═╗╔═╗╔╦╗╔═╗╔╦╗╦═╗╔═╗╔═╗
   ██║     ██╔═══██╗██╔════╝  │  ╠╩╗║ ║║ ║ ║ ╚═╗ ║ ╠╦╝╠═╣╠═╝
   ██║     ██║   ██║███████╗  │  ╚═╝╚═╝╚═╝ ╩ ╚═╝ ╩ ╩╚═╩ ╩╩
   ██║     ██║   ██║╚════██║  │
   ███████╗╚██████╔╝███████║  │
   ╚══════╝ ╚═════╝ ╚══════╝  ╵
```

[![CI](https://github.com/richardkfm/los-bootstrap/actions/workflows/ci.yml/badge.svg)](https://github.com/richardkfm/los-bootstrap/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-0.8.0-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android%20%2F%20LineageOS-brightgreen)](https://lineageos.org/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](CLAUDE.md)

A CLI-first toolkit for **LineageOS** and other AOSP-derived, degoogled
Android ROMs — covering the full journey from locked bootloader to a
hardened, privacy-audited daily driver.

> **Status:** Phase 8 — ROM flashing assistant. `los-bootstrap flash`
> guides you through bootloader unlock and ROM sideload with
> manufacturer-specific steps for Pixel, OnePlus, Fairphone, Motorola,
> Samsung (Heimdall), and Xiaomi (Mi Unlock Tool). All prior subcommands
> are unchanged. Mutating commands only run with explicit `--confirm`.
> See [`roadmap.md`](./roadmap.md) for what comes next.


<img width="426" height="240" alt="losbtstrp" src="https://github.com/user-attachments/assets/acef65f7-a59b-486f-a5cd-3c0abddbb7a1" />

## Why

Getting onto a degoogled ROM used to mean piecing together a dozen
forum posts: unlock the bootloader here, find the right recovery there,
figure out why location is broken, hunt for the right GCam port, and
remember which Google package crept back in. `los-bootstrap` covers
the whole process end-to-end from a single CLI:

- **Full lifecycle.** Bootloader unlock → ROM flash → privacy audit →
  hardening → app bootstrap → location diagnostics → camera tuning.
- **Honest about tradeoffs.** Every recommendation surfaces its downside.
  "Unlock your bootloader" also tells you about the verified-boot warning
  and data wipe. "Enable location" also tells you who can see it.
- **Manufacturer-aware.** Pixel/OnePlus (standard fastboot), Motorola
  (unlock key portal), Samsung (Heimdall + Odin fallback), Xiaomi
  (Mi Unlock Tool + mandatory waiting period) — each gets a real guide,
  not a generic "check your XDA thread."
- **CLI over GUI.** Every feature is reachable from the terminal.
  No web UI, no app to install on the device first.
- **Pluggable.** Device-specific knowledge lives in YAML, not `if`-trees.

## Install

Requires Python 3.10+ and the `adb` binary on `$PATH`.

**Getting Python, pip, and adb:**
- **macOS:** `brew install python android-platform-tools`
- **Ubuntu/Debian:** `sudo apt install python3 python3-pip android-tools-adb`
- **Arch Linux:** `sudo pacman -S python python-pip android-tools`
- **Windows:** Download from [python.org](https://www.python.org/downloads/) and
  [Android SDK tools](https://developer.android.com/studio/command-line/adb)
- **Other platforms:** See [Python docs](https://www.python.org/downloads/) and
  [ADB setup guide](https://developer.android.com/studio/command-line/adb)

### Clone and install

```bash
git clone https://github.com/richardkfm/los-bootstrap
cd los-bootstrap
python -m venv venv
source venv/bin/activate
pip install -e .
```

The virtual environment approach keeps your system Python clean and is
recommended for all platforms. Activate it each time with
`source venv/bin/activate`, or `deactivate` to exit.

**Non-bash shells (fish, etc.)?** The venv activate script is bash/zsh-only.
For **fish shell**, use:
```bash
source venv/bin/activate.fish
```
For other shells, temporarily switch to bash: `bash` then `source venv/bin/activate`.

**Arch Linux / PEP 668 error?** Modern Python distributions (including Arch)
protect system Python with PEP 668. The virtual environment setup above
handles this. If you see `externally-managed-environment`, ensure you've
created and activated the venv before running `pip install`.

**Windows users:** pip installs the `los-bootstrap` script into a `Scripts`
folder that is often not on `PATH`. If PowerShell reports the command is not
recognised, add the folder for the current session:

```powershell
$env:PATH += ";$(python -c 'import sysconfig; print(sysconfig.get_path(\"scripts\"))')"
```

To make it permanent across all sessions, run the same query through
`[Environment]::SetEnvironmentVariable` and restart PowerShell:

```powershell
$s = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
[Environment]::SetEnvironmentVariable("PATH", "$env:PATH;$s", "User")
```

## Quick start

### Flashing a ROM (Phase 8)

```bash
# 1. Check what state your device is in and identify the manufacturer
los-bootstrap flash status

# 2. Get the full bootloader unlock guide for your device (with live pre-checks)
los-bootstrap flash prepare

# 3. Verify your ROM zip targets the right device before flashing
los-bootstrap flash verify ~/Downloads/lineage-21-*.zip

# 4. Preview the flash sequence without running anything
los-bootstrap flash run ~/Downloads/lineage-21-*.zip --recovery ~/Downloads/recovery.img --dry-run

# 5. Execute the flash (destructive steps require --confirm)
los-bootstrap flash run ~/Downloads/lineage-21-*.zip --recovery ~/Downloads/recovery.img --confirm
```

### After the ROM is installed

Plug in your phone, enable USB debugging, accept the RSA prompt, then:

```bash
los-bootstrap                    # launch the interactive guided wizard
```

Or use individual subcommands directly:

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
The `camera`, `location compat`, and `flash prepare` commands work without a device.

## What it currently does

### ROM flashing assistant (Phase 8)

```bash
los-bootstrap flash status    # detect device state + manufacturer
los-bootstrap flash prepare   # manufacturer-aware unlock guide
los-bootstrap flash verify    # validate ROM zip
los-bootstrap flash run       # execute the flash sequence
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

### Interactive wizard and enriched output (Phase 6)

Run `los-bootstrap` with no arguments to launch the guided wizard:

- Detects your connected device and enters offline mode if none is found
- Main menu: Audit → Harden → Bootstrap → Location → Camera
- **Audit screen** — runs all checks and shows findings grouped into
  *issues to address* and *passing checks*, with word-wrapped prose
- **Drill-down** — select any finding for a full "what's happening / why
  it matters / how to fix it / tradeoff" explanation
- **Harden screen** — choose read-only report or interactive walk-through;
  per-finding confirmation before applying any fix
- **Bootstrap screen** — profile picker → plan review → apply with
  confirmation
- **Location / Camera screens** — same diagnostics as the subcommands
- **Offline mode** — no ADB device? Camera and Location compat still work

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
- It does not fetch ROMs from the network — you supply the zip file.
- It does not automate Samsung Odin (closed-source, Windows-only) or
  Xiaomi's Mi Unlock Tool (proprietary, server-enforced). It guides you
  through those manually.
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
