# CLAUDE.md

Living instruction file for any human contributors or Claude Code session working on this repo.
Read this top-to-bottom before making changes.

## Project purpose

`los-bootstrap` is a CLI-first, open-source post-install assistant for
LineageOS / AOSP-derived ROMs. It targets advanced users who already know
their way around `adb` and want to bootstrap a degoogled phone quickly,
audit privacy posture, and (eventually) apply opinionated hardening.

It can guide users through flashing a ROM and unlocking their bootloader,
and helps with everything that comes after the ROM is installed.

## Current scope (Phase 11 complete, version 0.14.x)

Audit MVP, bootstrap profiles, hardening assistant, location / maps
integration, camera / GCam port profiles, interactive wizard, ROM
flashing assistant (now with flash-lifecycle checks: ROM freshness, 
post-flash first-boot verification, pre-flash backup guidance), one-line
install distribution, and Android tablet support. Phases 1–11 have all
shipped; 0.13.0 layered cross-cutting CLI polish and bug fixes on top of
the Phases 1–10 scope. **No Phase 12 is scoped yet** — see `roadmap.md`
for how to propose one.

- Phase 1–5 (still in place): see prior changelog entries
- Phase 6 (still in place):
  - `los-bootstrap` (no args) — launches an interactive guided wizard
  - Menu-based navigation using `questionary` (with `input()` fallback)
  - `wizard/` package: `menu.py`, `prompt.py`, `prose.py`, `render.py`
  - Enriched finding output: grouped severity sections, word-wrapped prose,
    `→ Fix:` and `⚠ Tradeoff:` labels (used by both wizard drill-down and
    standalone reports)
  - Flash assistant reachable from the main menu (status, unlock guidance,
    ROM download, ROM verify, destructive flash with two-step confirm).

- Phase 1 (still in place):
  - Detect connected devices over ADB
  - Read ROM/build info via `getprop`
  - Run a privacy/degoogle audit (GMS, GSF, common Google packages,
    ADB-over-network, Private DNS, lockscreen presence)
  - Render a human-readable text report (and `--json`)
  - Surface non-binding bootstrap recommendations
- Phase 2 (still in place):
  - Profile schema with apps (source: `fdroid` / `aurora` / `sideload`)
    and settings (`namespace`, `key`, `value`, `note`)
  - `los-bootstrap plan --profile <name>` — dry-run a profile
  - `los-bootstrap apply --profile <name> --confirm` — execute the
    plan via `adb install` and `adb shell settings put`
  - Bundled starter profiles: `minimal`, `privacy-default`,
    `messaging-light`, `max-tools`, `camera`, shipped as package data
- Phase 3 (still in place):
  - `los-bootstrap harden` — read-only lockdown report with *why* and
    *tradeoff* for every finding
  - `los-bootstrap harden --interactive` — walk through each WARN/FAIL
    finding and offer to apply the fix (gated on `--confirm`)
  - `los-bootstrap harden --root` — adds SELinux check via `su`
  - Checks: developer options, USB debugging, screen lock, encryption
    state, unknown-sources flag, verified boot state, lockdown power-menu
    option, SELinux mode (root-only)
- Phase 4 (still in place):
  - `los-bootstrap location doctor` — read-only diagnostic of the location
    stack: location enabled, GMS conflict, microG presence, signature
    spoofing grant, UnifiedNlp backend inventory
  - `los-bootstrap location compat` — static app compatibility matrix
    (no device connection required)
  - `location/` package: `models.py`, `checks.py`, `report.py`, `compat.py`
- Phase 5 (current):
  - `los-bootstrap camera list-profiles` — list all known per-device GCam
    port profiles (no device connection required)
  - `los-bootstrap camera show <codename>` — show full port details and XML
    config path guidance for a device
  - `camera/` package: `models.py`, `profiles.py`, `report.py`
  - `profiles_data/camera.yml` — sideload bootstrap profile for LMC 8.4
  - Five device profiles: Pixel 7, Pixel 6, Redmi Note 10, OnePlus 9,
    Fairphone 4

- Phase 8 (still in place):
  - `los-bootstrap flash status` — detect device state (booted/fastboot/recovery) and manufacturer
  - `los-bootstrap flash prepare` — manufacturer-aware guided bootloader unlock wizard
    (full guidance for Pixel/OnePlus/Fairphone via fastboot, Motorola unlock key flow,
    Samsung via Heimdall with Odin fallback, Xiaomi with Mi Unlock Tool walkthrough)
  - `los-bootstrap flash download [<codename>]` — print ROM download links for
    the device and, with `--fetch`, pull the latest LineageOS zip from the
    official LOS JSON API with SHA-256 verification. Sister-distro page links
    (LineageOS for microG, /e/OS, DivestOS, CalyxOS, GrapheneOS, iodéOS) are
    always printed alongside the LOS entry.
  - `los-bootstrap flash verify <rom.zip>` — validate ROM file and check device codename match
  - `los-bootstrap flash run <rom.zip> [--recovery <img>] --confirm` — execute flash sequence
  - `flash/` package: `models.py`, `fastboot.py`, `heimdall.py`, `checks.py`,
    `guide.py`, `flash.py`, `report.py`, `distros.py`

- Phase 9 (still in place):
  - `scripts/install.sh` (POSIX) and `scripts/install.ps1` (PowerShell) —
    one-line installers that detect the host package manager, install
    `pipx` and `adb`, then run `pipx install "los-bootstrap[wizard]"`.
    Both print every command before executing and support `--dry-run`.
  - PyPI release flow with Trusted Publisher OIDC; `pipx install
    "los-bootstrap[wizard]"` is the canonical install path for users who
    already have Python.
  - GitHub Releases attach the install scripts and a SHA-256 checksum
    file alongside each tag.
  - `docs/RELEASING.md` documents the Trusted Publisher one-time setup.

- Phase 10 (still in place):
  - `DeviceFacts.form_factor` — new field reading `ro.build.characteristics`;
    `"tablet"` when it contains `"tablet"`, `"phone"` otherwise. Surfaced
    in `los-bootstrap info` output.
  - All user-visible "About phone" text replaced with form-factor-neutral
    language across wizard prose, flash unlock guides, and camera hints.
  - GCam port profiles for two LineageOS tablets: Xiaomi Pad 5 (nabu) and
    OnePlus Pad (jupiter).
  - ✓ Shipped in 0.12.0. Exit criteria met; see `roadmap.md`.

- Phase 10 follow-up polish (0.13.0, not a new phase):
  - Global options (`--serial/-s`, `--no-banner`, `--compact-banner`) now
    also accepted after the subcommand; `--version`/`-V` flag added.
  - Colorized report output (audit, harden, location doctor) on a TTY,
    honoring `NO_COLOR` / `FORCE_COLOR`.
  - Distinct exit code (3) for commands whose checks found issues,
    separate from exit code 2 (usage errors).
  - `flash status` detects Samsung Download Mode via `heimdall detect`.
  - Profile files with a `.yaml` extension are now discovered alongside
    `.yml`.
  - Notable fixes: microG was never actually detected in
    `location doctor` (wrong package id) and always produced a false
    "real GMS" warning; several flash-safety gaps (destructive steps not
    gated, wrong-codename ROM not blocked, `flash run` hanging on a
    booted device) were closed. Full list in `CHANGELOG.md`.

- Phase 11 (current):
  - `los-bootstrap flash update` — read-only "is my ROM current?" check
    against the LineageOS JSON API (exit code 3 when outdated;
    `--no-network` reports "unverifiable" instead of erroring)
  - `los-bootstrap flash check` — read-only post-flash first-boot
    verification (LineageOS detection, fingerprint, verified boot, A/B
    slot, GMS presence, build type; exit code 3 on any WARN/FAIL)
  - `los-bootstrap flash backup` — static pre-flash backup guidance
    (no device connection required)
  - `flash/lifecycle.py` (pure evaluators + ADB probe collector) and
    `flash/backup.py` (static guidance); ✓ Shipped in 0.14.0.
  - Freshness is compared within the device's own LineageOS major
    version; a newer major version is reported separately because it
    usually requires a full data wipe.
  - `flash check` exits 3 on a FAIL only. Warnings and probes that could
    not be read are reported without failing the command — a check that
    could not run must never render as a clean result.

If a change does not fit Phase 11 or the maintenance/polish of an
already-shipped phase, it goes in the roadmap, not the code.

## Non-goals

- Bypassing bootloader locks, vendor verification, or signature checks
- Auto-distributing GCam APKs or other proprietary binaries
- Running unsigned remote code or fetching a "config" from the network
- Pretending degoogled location is a solved problem
- Replacing what `adb` already does well; we wrap it, not rewrite it

## Architecture overview

```
src/los_bootstrap/
    __init__.py            # __version__ lives here
    cli.py                 # argparse entry point, prints logo
    logo.py                # ASCII logo + tagline
    adb.py                 # thin, testable wrapper around `adb`
    device.py              # getprop-derived device facts
    gms.py                 # shared com.google.android.gms classifier (microG vs real)
    _render_utils.py       # shared wrap() + partition_findings() helpers
    audit/
        __init__.py        # run_audit() orchestrator
        checks.py          # individual AuditCheck implementations
        models.py          # AuditFinding, Severity, AuditReport
    report.py              # render AuditReport as text or JSON
    bootstrap.py           # recommendations derived from findings
    profiles.py            # YAML profile loader + lookup
    plan.py                # build a reviewable Plan from a Profile
    apply.py               # execute a Plan via adb (mutating; --confirm)
    profiles_data/         # bundled starter profiles (package data)
        minimal.yml
        privacy-default.yml
        messaging-light.yml
        max-tools.yml
    harden/                # Phase 3 — hardening assistant
        __init__.py
        models.py          # HardenFinding, HardenReport, HardenStatus
        checks.py          # individual HardenCheck implementations
        report.py          # render_harden_report()
        interactive.py     # run_interactive() walk-through (mutating; --confirm)
    location/              # Phase 4 — location stack diagnostics
        __init__.py
        models.py          # LocationFinding, LocationReport, LocationStatus
        checks.py          # check functions + run_location_doctor()
        report.py          # render_location_report(), render_compat_matrix()
        compat.py          # static COMPAT_MATRIX (app compatibility data)
    camera/                # Phase 5 — GCam port profiles (no ADB required)
        __init__.py
        models.py          # CameraPort, CameraProfile, XmlConfig
        profiles.py        # static CAMERA_PROFILES (per-device data)
        report.py          # render_profile_list(), render_profile()
    flash/                 # Phase 8 — ROM flashing assistant
        __init__.py
        models.py          # DeviceState, Manufacturer, FlashStep, FlashPlan, RomMetadata
        fastboot.py        # thin wrapper around `fastboot` binary
        heimdall.py        # thin wrapper around `heimdall` CLI (Samsung)
        checks.py          # manufacturer detection, state detection, ROM validation
        guide.py           # manufacturer-aware bootloader unlock guidance text
        flash.py           # FlashPlan executor (mutating; --confirm gated)
        distros.py         # LineageOS API client + sister-distro download links
        report.py          # render_flash_status(), render_flash_plan(), render_download_options()
        lifecycle.py       # Phase 11 — ROM freshness + first-boot verification
                           #   (check_* functions + FIRST_BOOT_CHECKS, as in audit/)
        backup.py          # Phase 11 — static pre-flash backup guidance
    wizard/                # Phase 6 — interactive guided menu
        __init__.py        # run_wizard() entry point
        menu.py            # screens + routing
        prompt.py          # questionary adapter with input() fallback
        prose.py           # extended per-finding prose
        render.py          # enriched finding rendering used by wizard
scripts/                   # Phase 9 — one-line installers
    install.sh
    install.ps1
tests/
    test_audit.py          # pytest, mocks adb
    test_location.py       # pytest, mocks adb
    test_camera.py         # pytest, no adb (static data only)
```

Design rules:

- **CLI-first.** Every capability is reachable from `los-bootstrap <cmd>`.
- **Pure core, IO at edges.** `audit/checks.py` takes a `DeviceFacts`
  object and returns `AuditFinding`s. ADB IO is injected, not imported.
- **Pluggable device logic.** Device-specific quirks belong in YAML
  profiles, not in `if codename == "..."` branches.
- **Modes are separate concepts:**
  - *audit mode* — read-only (Phase 1)
  - *bootstrap mode* — propose/apply profile actions (Phase 2)
  - *hardening mode* — opinionated lockdown with explicit tradeoffs (P3)
  - *location mode* — read-only location stack diagnostics (P4)
  - *camera mode* — static GCam port profiles, no ADB required (P5)
  - *flash mode* — ROM flashing assistant with manufacturer-aware guidance (P8, current)
- **Mutation is gated.** The applier is the only place that calls
  mutating ADB methods (`install_apk`, `setting_put`), and only after
  the user passes `--confirm`. `plan` is read-only; so is everything
  in `audit/`.
- **Root is opt-in.** Anything requiring root sits behind an explicit
  `--root` flag and lives in a clearly named module.
- **Downloads from declared profile URLs are on by default** and documented.
  `source: fdroid` entries are resolved via the F-Droid API; `source: sideload`
  entries with a `url:` field are fetched directly. Use `--no-fetch` to opt out.
  Any other network access must be off by default and documented.

## Coding workflow

1. Confirm the change fits the current phase. If not, update `roadmap.md`
   first or push back to the user.
2. Keep functions small and composable. Prefer explicit over clever.
3. Default to no comments. Add one only when the *why* is non-obvious.
4. Add or update a pytest under `tests/` for new logic where reasonable.
5. Update docs and version metadata in the same change (see below).
6. Run `python -m pytest` before declaring done.

## Release / versioning policy

Semantic Versioning. Initial scaffold ships at `0.1.0`.

| Change                                       | Bump  |
|----------------------------------------------|-------|
| Doc-only fix, typo, internal refactor        | patch |
| Bug fix with no behavior change for users    | patch |
| New user-facing feature, command, or module  | minor |
| Breaking CLI flag, config, or profile schema | major |

**Every newly implemented user-facing feature requires a version bump
and a `CHANGELOG.md` entry in the same change.** Version lives in
`src/los_bootstrap/__init__.py` (`__version__`) and is read by
`pyproject.toml` via dynamic metadata, so bump it in one place.

## Changelog policy

`CHANGELOG.md` follows the "Keep a Changelog" style.

- Always keep an `## [Unreleased]` section at the top.
- Group entries under `Added`, `Changed`, `Fixed`, `Removed`, `Security`.
- On release, rename `Unreleased` to `## [x.y.z] - YYYY-MM-DD` and start
  a fresh empty `Unreleased` section above it.
- Every PR that changes behavior touches `CHANGELOG.md`.

## Roadmap discipline

**Do not build future phases early.** This is the single most important
rule for this project. If a contribution sneaks in Phase 4 work during
Phase 1, the diff must be split or rejected.

If the user asks for something out-of-phase:

1. Restate which phase it belongs to.
2. Ask whether to defer (preferred) or to formally promote that phase.
3. If promoted, update `roadmap.md` *first*, then implement.

## When scope changes

Any scope change requires updating, in the same change:

- `roadmap.md` (move work between phases, or change exit criteria)
- `CHANGELOG.md` (under `Unreleased`)
- `CLAUDE.md` "Current scope" section if Phase 1 itself shifts
- Version bump if user-facing

## Product philosophy reminders

- Reduce friction; do not pretend to remove it.
- Surface tradeoffs out loud. A recommendation without a downside is a
  bug.
- The tool must remain useful as a pure auditor even if the user never
  runs anything mutating.
- Be honest about device-specific behavior. "It depends on your phone"
  is an acceptable answer when it is the truthful one.
