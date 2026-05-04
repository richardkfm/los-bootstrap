# Roadmap

`los-bootstrap` is a CLI tool that helps advanced users flash and bootstrap
a LineageOS / AOSP-derived ROM on a degoogled device — from bootloader unlock
through post-install hardening and privacy audit.

The project is delivered in small, reviewable phases. Each phase has an
explicit goal, scope, exclusions, and exit criteria. **Future phases must
not be built early.** See `CLAUDE.md` for the rule.

---

## Phase 0 — Project framing

**Goal:** establish the project skeleton, vision, and contributor rules.

**Included:**
- `README.md`, `roadmap.md`, `CLAUDE.md`, `CHANGELOG.md`
- `pyproject.toml` with project metadata at `0.1.0`
- License (GPL-3.0, already present)
- Empty `src/los_bootstrap/` package layout
- Versioning + changelog discipline written down

**Excluded:** any runtime feature.

**Exit criteria:** a contributor can read `CLAUDE.md` and immediately know
how to add a feature, where to put it, and how to bump the version.

---

## Phase 1 — Audit MVP

**Goal:** read-only inspection of a connected device. The tool must be
useful as an auditor on day one even if no other phase ships.

**Included:**
- ADB integration: detect connected devices, run shell commands safely
- `los-bootstrap devices` — list connected devices
- `los-bootstrap info` — device, ROM, security patch, build info
- `los-bootstrap audit` — privacy/degoogle audit (GMS, GSF, common Google
  packages, ADB-over-network state, lockscreen presence, etc.)
- `los-bootstrap report` — render audit + info as a human-readable report,
  optional `--json`
- `los-bootstrap recommend` — non-binding bootstrap suggestions derived
  from audit findings (no apply step yet)
- Profiles directory (`profiles/`) with one example YAML, parsed but not
  yet applied
- Scaffolded but unimplemented modules for `location/` and `camera/`
- ASCII logo on CLI startup

**Excluded:**
- Any mutation of device state (no install, no settings change)
- microG / UnifiedNlp install flow
- GCam fetch or XML application
- Device-specific quirk handling beyond `ro.product.*` reads
- Root-only checks
- Network calls

**Exit criteria:** running `los-bootstrap audit` against a real LineageOS
device produces a clear, accurate, read-only report. CI/tests pass.
Version `0.1.0` tagged on first publish.

---

## Phase 2 — Bootstrap profiles

**Goal:** turn YAML profiles into actionable, reviewable bootstrap plans
the user can opt into.

**Included:**
- Profile schema (apps to install via F-Droid/Aurora, settings to suggest)
- `los-bootstrap plan --profile <name>` — dry-run a profile
- `los-bootstrap apply --profile <name> --confirm` — guided execution
  of non-destructive steps via `adb install` and `adb shell settings`
- Built-in starter profiles: `minimal`, `privacy-default`,
  `messaging-light`, `max-tools`
- Automatic APK downloads (on by default): `source: fdroid` entries are
  resolved via the F-Droid API; `source: sideload` entries with a `url:`
  field are fetched from that URL. Opt out with `--no-fetch`.

**Excluded:** anything that requires root, anything that touches `/system`.

**Exit criteria:** a user with a fresh LineageOS install can apply
`privacy-default` end-to-end and see the result reflected in `audit`.

---

## Phase 3 — Hardening assistant ✓

**Goal:** opinionated but transparent hardening guidance, with explicit
tradeoffs.

**Included:**
- Lockdown checks (developer options, ADB, USB debugging, screen lock,
  encryption state, lockdown mode, package installer source)
- `los-bootstrap harden --interactive` walking through each toggle with
  a "why" and "tradeoff" explanation
- Optional root-aware checks behind an explicit `--root` flag

**Excluded:** Magisk / KernelSU module installation. Custom kernel work.

**Exit criteria:** every recommendation has a documented rationale and a
documented downside. ✓ Shipped in 0.4.0.

---

## Phase 4 — Location / maps integration

**Goal:** make degoogled location workable for everyday apps (Telegram
location share, OsmAnd, etc.) without pretending it is solved.

**Included:**
- microG + UnifiedNlp setup guidance (signature spoofing prerequisites)
- Backend selection helper (Mozilla, DejaVu, local-only)
- Compatibility matrix: which apps work / partially work / don't
- `los-bootstrap location doctor` — diagnose location stack
- `los-bootstrap location compat` — app compatibility matrix

**Excluded:** flashing microG-signed ROMs. Anything proprietary.

**Exit criteria:** the limitations doc is accurate and the doctor command
reliably diagnoses the common failure modes. ✓ Shipped in 0.5.0.

---

## Phase 5 — Camera / GCam profiles ✓

**Goal:** treat camera tuning as the device-specific problem it is, and
help the user without overpromising.

**Included:**
- GCam port helper profiles (per-device, contributor-maintained)
- LMC / XML config path guidance
- `los-bootstrap camera list-profiles` and `... show <codename>`
- `profiles_data/camera.yml` bootstrap profile for sideloading LMC 8.4

**Excluded:** distributing GCam APKs (license concerns). Auto-tuning.

**Exit criteria:** at least three popular devices have working profiles
contributed by humans, not generated. ✓ Shipped in 0.6.0 with five devices.

---

## Phase 6 — Interactive wizard and enriched output ✓

**Goal:** lower the entry barrier by making `los-bootstrap` (no args)
launch a guided menu that covers audit → harden → bootstrap in a single
session. Enrich finding output with grouped severity sections, word-wrapped
prose, and contextual "what does this mean for me?" explanations.

**Included:**
- `los-bootstrap` (no args) → interactive wizard flow
- Menu-based navigation (questionary with `input()` fallback)
- `WizardContext` that caches ADB calls across back-navigation
- Offline mode: camera and location-compat available without a device
- Enriched grouped rendering for all finding reports (audit, harden,
  location). PASS findings compact; FAIL/WARN findings prose-wrapped with
  `→ Fix:` and `⚠ Tradeoff:` labels
- `wizard/prose.py` — extended contextual prose for all 15 audit/harden
  check IDs, accessible via `--verbose` on `audit` and `harden`
- All existing subcommands unchanged (backward compat)

**Excluded:** no new ADB checks, no new profiles.

**Exit criteria:** a first-time user can complete audit + basic harden in
one guided session without reading the README.

---

## Phase 7 — Device profile ecosystem (deferred)

**Goal:** make device-specific knowledge pluggable so the tool stays
useful as the LineageOS device list shifts.

> **Note:** this phase was deprioritised in favour of the ROM flashing
> assistant (Phase 8), which addressed a more immediate user need.
> Phase 7 work will resume after Phase 9.

**Included:**
- Device profile loader (codename → quirks, known issues, recommended
  toggles)
- Contributor workflow for adding device profiles
- Optional remote profile index (signed, opt-in)

**Excluded:** anything that runs unsigned remote code.

**Exit criteria:** adding a new device is a pull request that touches
only `profiles/devices/<codename>.yml` plus a test fixture.

---

## Phase 8 — ROM Flashing Assistant ✓

**Goal:** guide users through flashing a ROM on supported devices, from
bootloader unlock to first boot, with honest manufacturer-specific coverage.

**Included:**
- `fastboot/` and `heimdall/` wrappers (thin, injectable, no real device in tests)
- `los-bootstrap flash status` — detect device state (booted / fastboot / recovery /
  Samsung download mode) and identify manufacturer
- `los-bootstrap flash prepare` — manufacturer-aware bootloader unlock guide with
  live pre-checks (Developer Options, OEM unlocking flag) where device is in ADB mode:
  - Google / OnePlus / Fairphone: standard `fastboot flashing unlock` flow
  - Motorola: unlock-key retrieval via motorola.com, then `fastboot oem unlock <key>`
  - Samsung: step-by-step Heimdall guide (open-source, cross-platform); Odin
    fallback instructions printed when Heimdall is not installed
  - Xiaomi / Redmi / POCO: Mi Unlock Tool walkthrough (Windows, mandatory waiting
    period), with note that standard fastboot applies after the unlock is done
  - Generic / unknown: XDA-oriented generic fastboot guide
- `los-bootstrap flash verify <rom.zip>` — validate ROM file integrity and check
  `pre-device` metadata against connected device codename
- `los-bootstrap flash run <rom.zip> [--recovery <img>] --confirm` — execute the
  flash sequence; detects A/B vs A-only partition layout via `fastboot getvar slot-count`
- `flash/` package: `models.py`, `fastboot.py`, `heimdall.py`, `checks.py`,
  `guide.py`, `flash.py`, `report.py`

**Excluded:**
- Samsung Odin automation (closed-source, Windows-only)
- Xiaomi Mi Unlock Tool automation (proprietary, server-enforced waiting period)
- Fetching ROMs from the network (user supplies the file)
- Bypassing bootloader verification — we call official unlock APIs only

**Exit criteria:** a Pixel or OnePlus user can go from stock + locked bootloader
to sideloaded LineageOS using only `los-bootstrap flash *` commands. Samsung and
Xiaomi users receive accurate, actionable guidance even though those paths
require external tools. ✓ Shipped in 0.8.0.

---

## Phase 9 — Distribution and one-line install ✓

**Goal:** lower the install bar for novice LineageOS users from a
four-step clone-and-venv dance to a single command, without pretending
`adb` is something we can ship.

**Included:**
- PyPI release workflow (Trusted Publisher OIDC, no long-lived tokens)
- `los-bootstrap` published as a wheel and sdist; `pipx install
  "los-bootstrap[wizard]"` becomes the canonical install path for users
  who already have Python
- `scripts/install.sh` (POSIX `sh`) and `scripts/install.ps1`
  (PowerShell): detect the platform, ensure `pipx` and `adb` via the
  system package manager, then `pipx install "los-bootstrap[wizard]"`.
  Both scripts print every command before running, support `--dry-run`,
  and exit cleanly when the user declines or the package manager isn't
  recognised
- GitHub Releases workflow that attaches the install scripts and
  publishes a SHA-256 checksum file alongside each tag
- README install section rewritten: one-liner first, "from source" last
- `pyproject.toml` URL fixes (replace `example.invalid` placeholders)
  and the missing `[wizard]` extras group declaration
- `docs/RELEASING.md` documenting the one-time PyPI Trusted Publisher
  setup the maintainer performs before the first published release

**Excluded:**
- Bundling `adb`, `fastboot`, or `heimdall` (Google Platform Tools
  licensing and the project's existing "no proprietary binaries" rule)
- Self-contained PyInstaller / shiv binaries (deferred to Phase 9.1)
- Homebrew tap, winget manifest, Flatpak, AUR (deferred to Phase 9.1)
- Any auto-update or post-install network call beyond what `pip` /
  `pipx` already do — no remote config fetch, no telemetry

**Exit criteria:** a user on a fresh Ubuntu, macOS, or Windows machine
who has never installed Python can run the published one-liner and end
up with a working `los-bootstrap audit` against a connected device. The
install script is short enough (under 200 lines) that a contributor can
read and audit it in one sitting.

---

## Versioning at a glance

| Change                                  | Bump      |
|-----------------------------------------|-----------|
| Bug fix, doc-only fix                   | patch     |
| New feature, new module, new capability | minor     |
| Breaking CLI flag or config change      | major     |

The `Unreleased` section in `CHANGELOG.md` is the staging area between
releases. See `CLAUDE.md` for the full rule.
