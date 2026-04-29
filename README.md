```
   ██╗      ██████╗ ███████╗  ╷  ╔╗ ╔═╗╔═╗╔╦╗╔═╗╔╦╗╦═╗╔═╗╔═╗
   ██║     ██╔═══██╗██╔════╝  │  ╠╩╗║ ║║ ║ ║ ╚═╗ ║ ╠╦╝╠═╣╠═╝
   ██║     ██║   ██║███████╗  │  ╚═╝╚═╝╚═╝ ╩ ╚═╝ ╩ ╩╚═╩ ╩╩
   ██║     ██║   ██║╚════██║  │   post-install · degoogled
   ███████╗╚██████╔╝███████║  │   adb-driven · audit-first
   ╚══════╝ ╚═════╝ ╚══════╝  ╵
```

A CLI-first post-install assistant for **LineageOS** and other
AOSP-derived, degoogled Android ROMs. It does not flash ROMs. It helps
with everything that comes *after* you flash.

> **Status:** Phase 2 — Bootstrap profiles. Read-only by default; the
> `apply` command only runs mutating `adb` invocations with explicit
> `--confirm`. See [`roadmap.md`](./roadmap.md) for what comes next.

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
```

If you have more than one device connected, pass `--serial <id>`.

## What it currently does

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
- Builds and applies **profiles**: a YAML-described list of apps to
  install and `settings put` toggles. Bundled profiles:
  - `minimal` — F-Droid + Private DNS
  - `privacy-default` — adds maps, contacts, a browser, and DoT
  - `messaging-light` — Signal, Element, Telegram X
  - `max-tools` — broadest non-Google bundle: store, browser, maps,
    messaging, contacts/calendar, mail, media, productivity, password
    manager, RSS/podcasts, and **ReVanced Manager** for ad-free YouTube

### Automatic APK downloads

APKs are downloaded automatically when `apply` runs — no manual
staging required. Three download strategies are supported, declared
directly in profile YAML:

| Source in profile | How it's fetched |
|---|---|
| `source: sideload` + `url: https://…` | Downloaded directly |
| `source: sideload` + `url: github://owner/repo` | Latest `.apk` release asset from GitHub |
| `source: fdroid` | Resolved via the F-Droid API → downloaded from `f-droid.org/repo/` |
| `source: aurora` | Manual — Aurora Store handles Play Store apps |

Downloaded APKs are cached in `--apk-dir` so re-running `apply` skips
the network if the file already exists. Pass `--no-fetch` to disable
downloads entirely and revert to the old manual-staging behaviour.

No new dependencies: the downloader uses Python's stdlib `urllib` only.

### Applying a profile

```bash
# dry-run — shows what would be downloaded and installed
los-bootstrap plan --profile privacy-default

# apply — downloads APKs and installs them, then pushes settings
los-bootstrap apply --profile privacy-default --confirm

# cache APKs in a local directory for offline re-runs
los-bootstrap apply --profile privacy-default --apk-dir ~/los-apks --confirm

# opt out of downloads (manual staging as before)
los-bootstrap apply --profile privacy-default --no-fetch --apk-dir ~/los-apks --confirm
```

The plan output shows a `↓` glyph for steps that will be downloaded
and a `?` glyph for steps that require manual installation (Aurora
Store apps). Everything else shows the exact `adb` command that will run.

`apply` requires `--confirm` to execute any mutating command; `--dry-run`
lets you preview the full command list without touching the device or
the network.

## What it does NOT do (yet)

- It does not flash anything.
- It does not configure microG, UnifiedNlp, or location backends.
- It does not fetch or apply GCam ports / LMC XML configs.
- It does not require or offer root.
- It does not verify APK signatures — verify downloads out-of-band
  for security-critical installs (F-Droid, ReVanced Manager).

These are tracked in [`roadmap.md`](./roadmap.md).

## Project layout

See [`CLAUDE.md`](./CLAUDE.md) for the architecture, coding workflow,
versioning policy, and roadmap discipline rules.

## License

GPL-3.0. See `LICENSE`.
