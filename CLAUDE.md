# CLAUDE.md

Living instruction file for any Claude Code session working on this repo.
Read this top-to-bottom before making changes.

## Project purpose

`los-bootstrap` is a CLI-first, open-source post-install assistant for
LineageOS / AOSP-derived ROMs. It targets advanced users who already know
their way around `adb` and want to bootstrap a degoogled phone quickly,
audit privacy posture, and (eventually) apply opinionated hardening.

It does **not** flash ROMs. It assumes the ROM is already installed.

## Current scope (Phase 3, version 0.4.x)

Audit MVP, bootstrap profiles, and the hardening assistant:

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
    `messaging-light`, `max-tools`, shipped as package data
- Phase 3 (current):
  - `los-bootstrap harden` — read-only lockdown report with *why* and
    *tradeoff* for every finding
  - `los-bootstrap harden --interactive` — walk through each WARN/FAIL
    finding and offer to apply the fix (gated on `--confirm`)
  - `los-bootstrap harden --root` — adds SELinux check via `su`
  - Checks: developer options, USB debugging, screen lock, encryption
    state, unknown-sources flag, verified boot state, lockdown power-menu
    option, SELinux mode (root-only)
- Scaffold `location/` and `camera/` packages — placeholder only

If a change does not fit Phase 3, it goes in the roadmap, not the code.

## Non-goals

- Flashing ROMs, recoveries, or partitions
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
    location/              # SCAFFOLD — Phase 4
    camera/                # SCAFFOLD — Phase 5
tests/
    test_audit.py          # pytest, mocks adb
```

Design rules:

- **CLI-first.** Every capability is reachable from `los-bootstrap <cmd>`.
- **Pure core, IO at edges.** `audit/checks.py` takes a `DeviceFacts`
  object and returns `AuditFinding`s. ADB IO is injected, not imported.
- **Pluggable device logic.** Device-specific quirks belong in YAML
  profiles, not in `if codename == "..."` branches.
- **Modes are separate concepts:**
  - *audit mode* — read-only (Phase 1)
  - *bootstrap mode* — propose/apply profile actions (Phase 2, current)
  - *hardening mode* — opinionated lockdown with explicit tradeoffs (P3+)
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
