# los-bootstrap

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

> **Status:** Phase 1 — Audit MVP. Read-only. No device state is changed.
> See [`roadmap.md`](./roadmap.md) for what comes next.

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
  - Screen lock configuration
- Renders findings as a human-readable report (or JSON).
- Suggests bootstrap actions — without applying them.

## What it does NOT do (yet)

- It does not install or remove anything.
- It does not configure microG, UnifiedNlp, or location backends.
- It does not fetch or apply GCam ports / LMC XML configs.
- It does not require or offer root.

These are tracked in [`roadmap.md`](./roadmap.md).

## Project layout

See [`CLAUDE.md`](./CLAUDE.md) for the architecture, coding workflow,
versioning policy, and roadmap discipline rules.

## License

GPL-3.0. See `LICENSE`.
