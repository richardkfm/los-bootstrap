```
   ██╗      ██████╗ ███████╗  ╷  ╔╗ ╔═╗╔═╗╔╦╗╔═╗╔╦╗╦═╗╔═╗╔═╗
   ██║     ██╔═══██╗██╔════╝  │  ╠╩╗║ ║║ ║ ║ ╚═╗ ║ ╠╦╝╠═╣╠═╝
   ██║     ██║   ██║███████╗  │  ╚═╝╚═╝╚═╝ ╩ ╚═╝ ╩ ╩╚═╩ ╩╩
   ██║     ██║   ██║╚════██║  │   post-install · degoogled
   ███████╗╚██████╔╝███████║  │   adb-driven · audit-first
   ╚══════╝ ╚═════╝ ╚══════╝  ╵
```

# Roadmap

`los-bootstrap` is a CLI tool that helps advanced users get productive on a
freshly installed LineageOS / AOSP-derived ROM. It does not flash ROMs. It
helps with everything that comes after.

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

## Phase 3 — Hardening assistant (current)

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
documented downside.

---

## Phase 4 — Location / maps integration

**Goal:** make degoogled location workable for everyday apps (Telegram
location share, OsmAnd, etc.) without pretending it is solved.

**Included:**
- microG + UnifiedNlp setup guidance (signature spoofing prerequisites)
- Backend selection helper (Mozilla, DejaVu, local-only)
- Compatibility matrix: which apps work / partially work / don't
- `los-bootstrap location doctor` — diagnose location stack

**Excluded:** flashing microG-signed ROMs. Anything proprietary.

**Exit criteria:** the limitations doc is accurate and the doctor command
reliably diagnoses the common failure modes.

---

## Phase 5 — Camera / GCam profiles

**Goal:** treat camera tuning as the device-specific problem it is, and
help the user without overpromising.

**Included:**
- GCam port helper profiles (per-device, contributor-maintained)
- LMC / XML config path guidance
- `los-bootstrap camera list-profiles` and `... show <profile>`
- Verification steps before/after applying an XML config

**Excluded:** distributing GCam APKs (license concerns). Auto-tuning.

**Exit criteria:** at least three popular devices have working profiles
contributed by humans, not generated.

---

## Phase 6 — Device profile ecosystem

**Goal:** make device-specific knowledge pluggable so the tool stays
useful as the LineageOS device list shifts.

**Included:**
- Device profile loader (codename → quirks, known issues, recommended
  toggles)
- Contributor workflow for adding device profiles
- Optional remote profile index (signed, opt-in)

**Excluded:** anything that runs unsigned remote code.

**Exit criteria:** adding a new device is a pull request that touches
only `profiles/devices/<codename>.yml` plus a test fixture.

---

## Versioning at a glance

| Change                                  | Bump      |
|-----------------------------------------|-----------|
| Bug fix, doc-only fix                   | patch     |
| New feature, new module, new capability | minor     |
| Breaking CLI flag or config change      | major     |

The `Unreleased` section in `CHANGELOG.md` is the staging area between
releases. See `CLAUDE.md` for the full rule.
