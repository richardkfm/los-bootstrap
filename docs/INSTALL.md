# Installing los-bootstrap

[← README](../README.md) · [Install](INSTALL.md) · [Usage](USAGE.md) · [Features](FEATURES.md)

## One-liner (recommended)

**Linux / macOS:**

```bash
curl -fsSL https://raw.githubusercontent.com/richardkfm/los-bootstrap/main/scripts/install.sh | sh
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/richardkfm/los-bootstrap/main/scripts/install.ps1 | iex
```

The install script detects your OS, installs `pipx` and `adb` via your
system package manager (`apt` / `dnf` / `pacman` / `brew` / `winget`),
then runs `pipx install "los-bootstrap[wizard]"`. It prints every command
before running it, supports `--dry-run` (preview only), and exits cleanly
if your package manager isn't recognised.

**Audit-first variant** (recommended on machines you don't fully control):

```bash
curl -fsSL https://raw.githubusercontent.com/richardkfm/los-bootstrap/main/scripts/install.sh -o install.sh
sha256sum -c install.sh.sha256   # checksum is published on the GitHub Release
sh install.sh
```

**Caveats — surfaced honestly:**

- `adb` is required and is installed via your OS package manager, not
  bundled. On unusual distros or locked-down corporate machines the
  script will exit with a "install platform-tools manually" message.
- `fastboot` and `heimdall` are only needed for `flash run` and Samsung
  devices. The install script does **not** install them by default;
  the `flash` subcommand prints what to install when needed.
- Piping a script into `sh` is a trust decision. The script is in this
  repo (auditable diff), short enough to read in one sitting, and
  ships with a SHA-256 checksum on every release.

## If you already have Python and adb

```bash
pipx install "los-bootstrap[wizard]"
```

The `[wizard]` extra adds `questionary` for arrow-key menus. Without it
the wizard falls back to numbered `input()` prompts.

## Manual install (from source)

For users who'd rather read the code before installing anything, or for
contributors. Requires Python 3.10+ and the `adb` binary on `$PATH`.

```bash
git clone https://github.com/richardkfm/los-bootstrap
cd los-bootstrap
python -m venv venv
source venv/bin/activate                  # or: source venv/bin/activate.fish
pip install -e ".[wizard,dev]"
python -m pytest                          # optional sanity check
los-bootstrap version
```

On Windows, pip installs the `los-bootstrap` script into a `Scripts`
folder that is often not on `PATH` — `pipx` (used by the install scripts
above) handles this for you; in a manual venv install you may need to add
`Scripts` to `PATH` yourself.

**Arch Linux / PEP 668 error?** Modern Python distributions protect system
Python with PEP 668. The virtual environment above handles this; the
`pipx`-based one-liner above also handles it without a venv.

## Upgrade

To update an existing installation to the latest published release:

```bash
# One-liner / pipx users
pipx upgrade los-bootstrap
#   …or re-run the install script — it's idempotent and always pulls the
#   newest version from PyPI.

# Manual install (from source)
cd los-bootstrap
git pull
pip install -e ".[wizard,dev]"
```

Check the installed version any time with `los-bootstrap version`. The
project follows Semantic Versioning; see [`CHANGELOG.md`](../CHANGELOG.md)
for what each release changed.
