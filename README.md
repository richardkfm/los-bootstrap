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
  install (via `adb install` for sideloaded APKs, or queued for
  F-Droid / Aurora) and `settings put` toggles. Bundled profiles:
  `minimal`, `privacy-default`, `messaging-light`, `max-tools`
  (broadest non-Google bundle: store, browser, maps, messaging,
  contacts/calendar, mail, media, productivity, password manager,
  RSS / podcasts).

### Applying a profile

```bash
# 1. (one-time) stage any sideload APKs the profile references
mkdir -p ~/los-bootstrap-apks
curl -L -o ~/los-bootstrap-apks/F-Droid.apk https://f-droid.org/F-Droid.apk
# verify the signature before continuing.

# 2. dry-run: see exactly what would change
los-bootstrap plan --profile privacy-default --apk-dir ~/los-bootstrap-apks

# 3. apply
los-bootstrap apply --profile privacy-default --apk-dir ~/los-bootstrap-apks --confirm
```

`apply` will sideload any `source: sideload` apps it has APKs for, push
each setting via `adb shell settings put`, and print the remaining
F-Droid / Aurora apps as manual follow-ups (the tool never reaches out
to a store on your behalf).

## What it does NOT do (yet)

- It does not flash anything.
- It does not configure microG, UnifiedNlp, or location backends.
- It does not fetch or apply GCam ports / LMC XML configs.
- It does not require or offer root.
- It does not download APKs for you. Sideloaded APKs must already be
  on disk and verified before `apply` runs.

These are tracked in [`roadmap.md`](./roadmap.md).

## Project layout

See [`CLAUDE.md`](./CLAUDE.md) for the architecture, coding workflow,
versioning policy, and roadmap discipline rules.

## License

GPL-3.0. See `LICENSE`.
