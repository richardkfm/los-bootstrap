# Changelog

All notable changes to `los-bootstrap` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

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
