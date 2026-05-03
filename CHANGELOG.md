# Changelog

All notable changes to `los-bootstrap` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

## [0.9.0] - 2026-05-03

### Added
- Phase 9: distribution and one-line install. The project can now be
  installed with a single shell command instead of cloning the repo
  and creating a virtualenv by hand.
- `scripts/install.sh` (POSIX `sh`) — detects the host OS via `uname`
  and `/etc/os-release`, ensures `pipx` and `adb` are installed via the
  system package manager (`apt`, `dnf`, `pacman`, `brew`), and then
  runs `pipx install "los-bootstrap[wizard]"`. Prints every command
  before running it, supports `--dry-run` and `--yes`, refuses to run
  as root unless `--allow-root` is passed, and exits with a clear
  "install platform-tools manually" message when the package manager
  isn't recognised.
- `scripts/install.ps1` — Windows PowerShell equivalent. Uses `winget`
  (preferred) or `scoop` to install Python and `android-platform-tools`,
  then runs `pipx ensurepath` and `pipx install "los-bootstrap[wizard]"`.
- `.github/workflows/publish.yml` — builds sdist + wheel on `v*` tags,
  publishes to PyPI via Trusted Publishing (OIDC, no long-lived tokens),
  and attaches the install scripts plus a SHA-256 checksum file to the
  GitHub Release.
- `docs/RELEASING.md` — documents the one-time PyPI Trusted Publisher
  setup the maintainer performs once, and the per-release tag-and-push
  flow.
- README install section rewritten: leads with the one-liner for
  Linux/macOS and Windows; `pipx install` shown as the second tier;
  `git clone` flow demoted to a "From source" appendix for contributors.
- `[project.optional-dependencies] wizard = ["questionary>=2.0"]`
  declared in `pyproject.toml`. The `los-bootstrap[wizard]` extras
  group was previously documented in the README but missing from the
  package metadata, so `pip install "los-bootstrap[wizard]"` failed.

### Changed
- `pyproject.toml` project URLs updated from `example.invalid`
  placeholders to `https://github.com/richardkfm/los-bootstrap`.
  `Changelog` URL added under `[project.urls]`.
- `roadmap.md`: Phase 9 (distribution and one-line install) added.

### Fixed
- `pip install "los-bootstrap[wizard]"` now works (the `wizard` extras
  group was missing from `pyproject.toml`).

## [0.8.0] - 2026-05-03

### Added
- Phase 8: ROM flashing assistant. `los-bootstrap flash` is a new subcommand
  group that guides users from a locked bootloader to a sideloaded LineageOS ROM.
- `los-bootstrap flash status` — detect device state (booted, fastboot, recovery,
  Samsung download mode) and manufacturer from ADB/fastboot output.
- `los-bootstrap flash prepare` — manufacturer-aware guided bootloader unlock with
  live pre-checks (Developer Options, OEM unlocking) where the device is accessible
  via ADB. Covers Google / OnePlus / Fairphone (standard `fastboot flashing unlock`),
  Motorola (unlock-key portal flow), Samsung (Heimdall open-source path with Odin
  fallback instructions), and Xiaomi / Redmi / POCO (Mi Unlock Tool walkthrough with
  mandatory waiting-period caveat). Generic fastboot guidance for unrecognised devices.
- `los-bootstrap flash verify <rom.zip>` — validates the ROM zip, extracts
  `pre-device` from OTA metadata, and compares it against the connected device
  codename to catch wrong-device mistakes before flashing.
- `los-bootstrap flash run <rom.zip> [--recovery <img>] [--confirm] [--dry-run]` —
  executes the flash sequence. Detects A/B vs A-only partition layout via
  `fastboot getvar slot-count`. Mutating steps are gated behind `--confirm`.
- `src/los_bootstrap/flash/` package: `models.py` (DeviceState, Manufacturer,
  FlashStep, FlashPlan, RomMetadata, FlashStepKind), `fastboot.py` (Fastboot
  wrapper with injectable runner), `heimdall.py` (Heimdall wrapper, Samsung),
  `checks.py` (manufacturer detection, state detection, ROM metadata parsing),
  `guide.py` (full manufacturer-specific unlock guidance text),
  `flash.py` (plan executor), `report.py` (status and plan renderers).
- `Adb.reboot(target)` and `Adb.sideload(zip_path)` added to the ADB wrapper.

### Changed
- Project description updated: `los-bootstrap` now covers ROM flashing as well
  as post-install bootstrap. "Does not flash ROMs" removed from project purpose.
- `roadmap.md`: Phase 8 (ROM Flashing Assistant) added; Phase 7 (device profile
  ecosystem) unchanged.
- `CLAUDE.md`: "Flashing ROMs, recoveries, or partitions" removed from Non-goals;
  current scope updated to Phase 8.

## [0.7.0] - 2026-04-30

### Added
- Phase 6: interactive wizard. Running `los-bootstrap` with no arguments now
  launches a menu-based guided flow covering audit, harden, bootstrap,
  location, and camera in a single session. No subcommand knowledge required.
- `src/los_bootstrap/wizard/` package: `menu.py` (screen routing and
  `WizardContext`), `prompt.py` (questionary adapter with `input()` fallback),
  `prose.py` (contextual prose for all 15 audit/harden findings),
  `render.py` (grouped finding display and full finding detail helpers).
- Enriched output on all finding renderers: findings are now grouped into
  actionable issues and informational sections. PASS findings show as a
  compact tick-only line; FAIL/WARN findings show wrapped prose paragraphs
  with clearly labelled `→ Fix:` and `⚠ Tradeoff:` blocks.
- `--verbose` flag on `audit` and `harden` subcommands to get the wizard-style
  enriched prose without entering the interactive wizard.
- `questionary>=2.0` added as an optional `[wizard]` extra; the wizard falls
  back to numbered `input()` prompts when questionary is not installed.

### Changed
- `los-bootstrap` with no arguments now launches the interactive wizard
  instead of printing help text. Use `los-bootstrap --help` for the full
  command reference.
- All finding renderers (`report.py`, `harden/report.py`,
  `location/report.py`) now omit the internal `id:` and raw `state:` fields
  from default output. Findings are grouped by severity and long prose is
  word-wrapped at 72 characters. The `--json` output is unchanged.
- `roadmap.md`: Phase 6 is now the interactive wizard; former Phase 6
  (device profile ecosystem) becomes Phase 7.

## [0.6.1] - 2026-04-30

### Fixed
- README Install section now includes a Windows PATH note explaining how to
  add the Python `Scripts` folder for the current session and permanently.

## [0.6.0] - 2026-04-29

### Added
- Phase 5: camera / GCam port profiles.
- `los-bootstrap camera list-profiles` — list all known per-device GCam port
  profiles. No device connection required.
- `los-bootstrap camera show <codename>` — print the full GCam port profile for
  a device, including port name, verified status, source guidance, and the exact
  `adb push` command to apply each XML config.
- `src/los_bootstrap/camera/` package: `models.py` (CameraPort, CameraProfile,
  XmlConfig dataclasses), `profiles.py` (static CAMERA_PROFILES tuple),
  `report.py` (render_profile_list, render_profile).
- `find_camera_profile(codename)` — case-insensitive codename lookup exposed
  from the camera package public API.
- Bundled GCam port profiles for five real devices: Google Pixel 7 (panther),
  Google Pixel 6 (oriole), Xiaomi Redmi Note 10 (sunny), OnePlus 9 (lemonade),
  and Fairphone 4 (FP4). Each profile includes: verified/unverified tag per
  port, source guidance for obtaining the APK, device-specific notes, and XML
  config entries with device path and apply hint.
- `profiles_data/camera.yml` — bootstrap profile for sideloading LMC 8.4.
  Installs from a manually staged `lmc84.apk`; GCam APKs are never
  auto-fetched. Pairs with `camera show <codename>` for XML config guidance.
- XML config path guidance for LMC 8.4 and BSG 9.3: all XML files are expected
  at `/sdcard/GCam/Config/` (standard LMC path). Apply hint in each profile
  shows the exact `adb push` command.

## [0.5.0] - 2026-04-29

### Added
- Phase 4: location / maps integration.
- `los-bootstrap location doctor` — read-only diagnostic of the device's
  location stack: checks whether location is enabled, whether real GMS
  conflicts with microG, whether microG GmsCore is installed, whether
  microG has the `FAKE_PACKAGE_SIGNATURE` (signature spoofing) permission
  granted, and which UnifiedNlp network-location backends are installed.
  Every finding carries a *why* and a *tradeoff*, matching Phase 3 style.
- `los-bootstrap location compat` — print the static app compatibility
  matrix showing which apps work fully, partially (needs microG), GPS-only,
  or not at all on a degoogled ROM. No device connection required.
- `src/los_bootstrap/location/` package: `models.py` (data classes),
  `checks.py` (five check functions + `run_location_doctor()` orchestrator),
  `report.py` (`render_location_report()` and `render_compat_matrix()`),
  `compat.py` (static `COMPAT_MATRIX` with 14 real-world app entries).
- Compatibility matrix covers: OsmAnd, Organic Maps, Magic Earth, Google
  Maps, Telegram, Signal, WhatsApp, Element, Firefox, Brave, Chromium /
  Vanadium, Uber / Lyft, F-Droid, and weather apps.

## [0.4.0] - 2026-04-29

### Added
- Phase 3: hardening assistant. `los-bootstrap harden` runs a suite of
  read-only lockdown checks and prints a report with severity, rationale,
  and tradeoff for every finding.
- `los-bootstrap harden --interactive` walks through each WARN/FAIL finding
  one at a time, explains the *why* and *tradeoff*, and offers to apply the
  fix. Fixes only execute with `--confirm`; `--dry-run` previews the exact
  `adb shell` command without running it.
- `los-bootstrap harden --root` adds SELinux-mode check via `su -c getenforce`.
  Root-only checks are skipped entirely when `--root` is not passed.
- Hardening checks implemented: developer options (`dev.options`), USB
  debugging (`dev.adb`), screen lock (`sec.screen_lock`), storage
  encryption (`sec.encryption`), unknown-sources flag
  (`sec.unknown_sources`), verified boot state (`sec.verified_boot`),
  lockdown power-menu option (`sec.lockdown_menu`), and SELinux mode
  (`sec.selinux`, root-only).
- `src/los_bootstrap/harden/` package: `models.py` (data classes),
  `checks.py` (check implementations + orchestrator), `report.py` (text
  renderer), `interactive.py` (walk-through engine).
- `max-tools` profile now includes Wero (`eu.epicompany.wero.wallet`)
  via Aurora Store as an EU payment option. Note documents the
  regional limitation and the Play Integrity attestation wall that
  most payment apps hit on degoogled ROMs.

## [0.3.0] - 2026-04-28

### Added
- Automatic APK downloads, on by default. `source: fdroid` entries are
  resolved via the F-Droid API (`suggestedVersionCode`) and downloaded
  directly from `f-droid.org/repo/`. `source: sideload` entries with a
  `url:` field are downloaded from that URL when the APK is not already
  present in `--apk-dir`. Downloads are cached: re-running `apply` with
  the same `--apk-dir` skips the network call.
- `--no-fetch` flag on both `plan` and `apply` to opt out of automatic
  downloads; sideload and F-Droid entries revert to manual/missing-APK
  behaviour as in 0.2.0.
- `src/los_bootstrap/fetch.py` — stdlib-only downloader (`urllib.request`
  + `json`, no new dependencies). Supports `fdroid://` scheme for
  F-Droid API resolution, `github://owner/repo` scheme for GitHub
  release assets, and plain HTTPS for direct downloads. Raises
  `FetchError` on HTTP or network failures.
- `max-tools` profile: added ReVanced Manager (`github://ReVanced/revanced-manager`,
  auto-downloaded from latest GitHub release) and a YouTube APK sideload
  entry with instructions for manual staging (version must match
  ReVanced patch requirements; no auto-download for proprietary APKs).

### Changed
- `CLAUDE.md` "No hidden network" rule relaxed: downloads from URLs
  declared in the active profile are on by default and documented;
  any other network access remains off by default.
- `los-bootstrap apply` now accepts `--apk-dir` as a download cache
  directory in addition to a staging directory.

## [0.2.0] - 2026-04-28

### Added
- Phase 2: bootstrap profiles. Profiles describe apps to install and
  device settings to suggest, expressed as YAML.
- Profile schema extension: each app entry can declare `source`
  (`fdroid`, `aurora`, or `sideload`), an optional `apk` filename for
  sideloaded APKs, an informational `url`, and a `note` explaining the
  rationale. Settings entries gain an optional `note`. Plain-string
  app entries are still accepted as shorthand for `{source: fdroid}`.
- `los-bootstrap plan --profile <name>`: build and print a per-step
  plan for a profile, showing what would be installed, what would be
  changed, and what is already satisfied. Read-only.
- `los-bootstrap apply --profile <name> --confirm`: execute the plan.
  Mutating commands run only with `--confirm`; `--dry-run` previews
  the literal `adb` invocations without running them.
- `los-bootstrap profiles list`: list bundled profiles.
- Bundled profiles: `minimal`, `privacy-default` (refresh),
  `messaging-light`, and `max-tools` (broad coverage of everyday tools
  without GMS — store, browser, maps, messaging, contacts/calendar,
  mail, media, productivity, password manager + 2FA, RSS/podcasts).
  They ship inside the package as
  `los_bootstrap/profiles_data/*.yml`.
- New audit check `dns.private`: flags whether Private DNS is off,
  opportunistic, or hostname-pinned. Closes the loop so applying
  `privacy-default` is reflected in `audit`.
- ADB wrapper gained `setting_get`, `setting_put`, and `install_apk`.
  These are mutating; only the applier calls them, and only after the
  user passes `--confirm`.

### Changed
- Profiles directory moved from the top-level `profiles/` into the
  package at `src/los_bootstrap/profiles_data/` so they ship with
  `pip install`. Profile lookup now searches: explicit path → any
  `--profile-dir` overrides → bundled profiles.

### Security
- `apply` refuses to mutate device state unless `--confirm` is passed.
  No code paths reach `adb install` or `adb shell settings put`
  outside the applier.

## [0.1.0] - 2026-04-28

### Added
- Initial Phase 1 (Audit MVP) scaffold.
- `los-bootstrap` CLI entry point with custom ASCII logo on startup.
- `los-bootstrap devices` — list ADB-connected devices.
- `los-bootstrap info` — print device, ROM, build, and security-patch
  information read from `getprop`.
- `los-bootstrap audit` — read-only privacy/degoogle audit (GMS, GSF,
  common Google packages, ADB-over-network state, lockscreen presence).
- `los-bootstrap report` — render audit results as text or `--json`.
- `los-bootstrap recommend` — non-binding bootstrap recommendations
  derived from audit findings.
- ADB wrapper module with injected runner for testability.
- YAML profile loader (`profiles.py`) — parse-only, not applied yet.
- Example profile `profiles/privacy-default.yml`.
- Scaffold packages `src/los_bootstrap/location/` and `.../camera/` with
  explicit `NotImplementedError` placeholders for future phases.
- `roadmap.md`, `CLAUDE.md`, `README.md`.
- `pytest` suite covering audit logic with mocked ADB output.

### Security
- All Phase 1 commands are strictly read-only. No state-changing ADB
  commands are issued.

[Unreleased]: https://example.invalid/los-bootstrap/compare/v0.2.0...HEAD
[0.2.0]: https://example.invalid/los-bootstrap/compare/v0.1.0...v0.2.0
[0.1.0]: https://example.invalid/los-bootstrap/releases/tag/v0.1.0
