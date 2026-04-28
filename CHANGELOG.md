# Changelog

All notable changes to `los-bootstrap` are documented here.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
and the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

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

[Unreleased]: https://example.invalid/los-bootstrap/compare/v0.1.0...HEAD
[0.1.0]: https://example.invalid/los-bootstrap/releases/tag/v0.1.0
