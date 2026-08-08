# Changelog

All notable changes to `los-bootstrap` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

## [0.13.0] - 2026-07-06

### Added
- Global options (`--serial/-s`, `--no-banner`, `--compact-banner`) are now
  accepted after the subcommand too: `los-bootstrap flash status -s XYZ`
  works, not just `los-bootstrap -s XYZ flash status`.
- `--version`/`-V` flag on the main parser (alongside the existing
  `version` subcommand), plus usage examples and an exit-code legend in
  `--help`.
- Report output (audit, harden, location doctor) is colorized when stdout
  is a TTY: green/yellow/red status glyphs and summary lines. Honors
  `NO_COLOR` and `FORCE_COLOR`; JSON output is never colorized.
- `flash status` now detects Samsung Download Mode via `heimdall detect`
  when no ADB or fastboot device is visible and Heimdall is installed.
- Profile files with a `.yaml` extension are now found alongside `.yml`.

### Changed
- Distinct exit code for findings: commands that run checks (`audit`,
  `report`, `harden`, `location doctor`, `flash verify`) now exit **3**
  when issues need attention, instead of overloading **2**, which argparse
  already uses for usage errors. Documented in README and `--help`.
- `--serial` with a serial that is not connected (or not authorized) now
  fails immediately with a clear message listing the connected devices,
  instead of failing later with a raw adb error.
- The interactive harden walk-through offers the USB-debugging fix last and
  prints a notice when it is applied, since that fix severs the tool's own
  ADB connection.

### Fixed
- Downloaded APKs are validated as zip containers before `adb install`;
  a truncated download or HTML error page is deleted instead of being
  installed or poisoning the download cache.
- The wizard no longer shows a spurious "Device error" splash before the
  device picker when multiple devices are connected (and no longer shows
  the splash twice).
- The wizard's ROM download screen no longer prints the CLI-only
  "Re-run with --fetch" hint.
- microG detection in `location doctor` now looks at the real package id.
  microG GmsCore installs as `com.google.android.gms` (not the non-existent
  `org.microg.gms.core` the checks previously queried), so microG was never
  detected and every microG device got a false "Real Google Play Services
  detected" warning. The doctor now classifies the installed GMS package by
  its versionName (microG has always shipped 0.x) and reports microG,
  real GMS, or "could not classify" honestly.
- `flash run` no longer hangs forever when the device is booted:
  `fastboot getvar slot-count` blocks until a fastboot device appears, so the
  A/B check now only queries fastboot in fastboot mode and reads
  `ro.boot.slot_suffix` over ADB when booted. Same fix in the wizard.
- `flash run` (CLI) now refuses to flash a ROM whose OTA metadata targets a
  different device codename than the connected device; the wizard warns and
  requires an explicit extra confirmation. `flash verify` now exits non-zero
  on a codename mismatch, not only on a corrupt zip.
- Destructive flash steps (`fastboot flash`, `fastboot update`,
  `adb sideload`, `heimdall flash`) are now marked `is_destructive`, so the
  executor's `--confirm` gate actually protects them and the plan preview
  shows the "DESTRUCTIVE" tag.
- The flash executor now pauses on MANUAL steps until the user confirms the
  action is done, instead of immediately running the next command (e.g.
  running `heimdall flash` before the device was in Download Mode). Flash
  plans also gained an explicit "Apply update → Apply from ADB" step before
  every sideload.
- `fastboot reboot` / `fastboot flashing unlock` failures now raise instead
  of being silently counted as successful steps.
- The applier no longer reports a step as "ok" when it could not parse the
  step's command; it records an error and executes nothing.
- Hardening check for the power-menu lockdown option now uses the real AOSP
  settings key `lockdown_in_power_menu` (was the non-existent
  `lockdown_mode_allowed`, which made the check always warn and the fix a
  no-op).
- Boolean profile setting values are stored as `1`/`0` instead of the
  literal strings `True`/`False`, matching what `settings put` expects.
- `adb devices` daemon-startup chatter (`* daemon not running; ...`) is no
  longer parsed as a device.
- `flash download` rejects the contradictory `--fetch --no-network`
  combination up front instead of failing with a misleading error.
- Wizard's ROM download screen now falls back to `ctx.get_facts().codename`
  when the flash-context detection didn't pick up a codename (e.g. device
  in fastboot mode at wizard start, or transient `getprop` failure). The
  prompt then offers the device's actual codename as the default instead
  of forcing the user to type it manually.

## [0.12.1] - 2026-05-07

### Fixed
- Wizard's ROM download screen now queries the LineageOS API first,
  shows the build's filename/version/size/SHA-256, and only then asks
  for confirmation before downloading. The download itself prints live
  `MiB / total MiB (%)` progress so a multi-GiB transfer no longer looks
  like the wizard has hung on "Querying LineageOS API…".

## [0.12.0] - 2026-05-07

### Added
- Phase 10: Android tablet support.
- `DeviceFacts.form_factor` — new field derived from `ro.build.characteristics`.
  Set to `"tablet"` when the property contains `"tablet"`, `"phone"` otherwise.
  Surfaced in `los-bootstrap info` output.
- GCam port profiles for two LineageOS-supported tablets:
  - Xiaomi Pad 5 (nabu) — Snapdragon 860, LMC 8.4 R17, verified working on LineageOS 21.
  - OnePlus Pad (jupiter) — Dimensity 9000, LMC 8.4 R17, verified working on LineageOS 21.

### Changed
- All user-visible "About phone" references replaced with form-factor-neutral
  language ("About phone / About tablet" or "About device") in wizard prose,
  flash unlock guides, and camera report hints. Tablets are now first-class citizens.
- Test helpers updated to include the new `form_factor` field.

## [0.11.0] - 2026-05-06

### Added
- Wizard now exposes the flash assistant under a new "Flash — bootloader
  unlock + ROM flashing" entry on the main menu. The screen detects device
  state (booted / fastboot / recovery) and offers four sub-flows:
  - bootloader unlock guidance (read-only),
  - ROM download via the LineageOS API with optional `--fetch`-equivalent
    download + SHA-256 verification, and sister-distro page links,
  - ROM zip verification (zip integrity + OTA codename match),
  - destructive ROM flash with a two-step confirmation gate before the
    flash plan is executed.
- README badge bumped to 0.11.0.

### Changed
- README: added an ASCII function tree of the wizard's screens at the
  top of the wizard section so the full menu hierarchy (Audit, Harden,
  Bootstrap, Location, Camera, Flash and their sub-flows) is visible at
  a glance. Added a "Flash screen" bullet in the wizard description and
  updated the offline-mode bullet to mention that most Flash sub-screens
  also work without ADB. Removed the now-redundant "Main menu: …" bullet.
- README: replaced the stale "It does not fetch ROMs from the network"
  claim under "What it does NOT do" with an accurate description of
  `flash download --fetch` (LineageOS API only, SHA-256 verified).
- roadmap.md: added a Phase 8 follow-on note recording that the flash
  assistant is now reachable from the wizard (shipped in 0.11.0).

## [0.10.0] - 2026-05-06

### Fixed
- Wizard splash no longer prints the version twice (the ASCII banner
  already includes the version footer).
- Wizard's interactive harden flow now correctly aborts when the user
  declines to apply fixes, instead of walking through findings in a
  misleading dry-run mode.
- Wizard's bootstrap plan now fetches APKs by default, matching the
  CLI's `plan` / `apply` behavior (was silently `fetch=False`).
- Removed the redundant offline-mode message in the wizard splash —
  the device line already states whether the wizard is offline.
- `plan.py` setting lookup now catches `AdbCommandError` specifically
  rather than every `Exception`, so unrelated bugs surface instead of
  silently defaulting the current value to empty.

### Changed
- README: bumped version badge to 0.10.0, renamed "From source
  (contributors)" to "Manual install (from source)" and added a sanity
  check, and added a new `## Upgrade` section covering pipx, the
  one-liner installer, and source installs.
- CLAUDE.md: "Current scope" now reads Phase 9 / 0.10.x; added a Phase 9
  block summarising `scripts/install.sh` / `install.ps1`; added the
  `harden/` package and `wizard/` package to the architecture overview;
  added the new `_render_utils.py` module.
- Removed the documented `--verbose` flag on `audit` / `harden` from
  CLAUDE.md and roadmap.md — it was never implemented; the wizard's
  drill-down screen is the canonical way to read enriched prose.
- Internal: extracted shared `wrap()` and `partition_findings()` helpers
  into `_render_utils.py` and reused them across `report.py`,
  `location/report.py`, `harden/report.py`, and `wizard/render.py`.
- Internal: deduplicated flash device-detection boilerplate behind a
  new `_detect_flash_context()` helper used by `cmd_flash_status`,
  `cmd_flash_prepare`, and `cmd_flash_run`. No CLI behavior changes.

### Added
- `los-bootstrap flash download [<codename>]` — print ROM download links
  for the connected device (or an explicit codename) and, with `--fetch`,
  download the latest LineageOS nightly zip and verify its SHA-256.
  Queries the LineageOS public JSON API
  (`download.lineageos.org/api/v2/devices/<codename>/builds`) to pick the
  newest build; surfaces filename, version, size, SHA-256 and direct URL.
  `--no-network` skips the API call and prints the LOS download page URL
  only. Falls back gracefully when the device is not officially supported.
- Sister-distro download links printed alongside the LineageOS entry:
  LineageOS for microG, /e/OS, DivestOS, CalyxOS, GrapheneOS, iodéOS.
  Distros without a stable per-codename URL get their main install
  landing page instead.
- `flash/distros.py` module: `lookup_lineage_build`, `download_lineage_zip`
  (with streaming + SHA-256 verification + cache hit on already-downloaded
  files), `lineage_device_url`, `alt_distro_links`.
- `tests/test_flash_distros.py` — full coverage with mocked HTTP openers
  (no real network access in tests).

### Changed
- Replaced CLI ASCII logo with a hollow outline-font style for "LOS" and a tile-box style for "BOOTSTRAP".
- Phase 8 scope expanded to include user-driven ROM download. The previous
  exclusion ("Fetching ROMs from the network") in `roadmap.md` is replaced
  with a tighter scope: explicit, opt-in fetches from the publisher's own
  API, with hash verification, only when the user runs `flash download`.

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

[Unreleased]: https://github.com/richardkfm/los-bootstrap/compare/v0.13.0...HEAD
[0.13.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.12.1...v0.13.0
[0.12.1]: https://github.com/richardkfm/los-bootstrap/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/richardkfm/los-bootstrap/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/richardkfm/los-bootstrap/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/richardkfm/los-bootstrap/releases/tag/v0.1.0
