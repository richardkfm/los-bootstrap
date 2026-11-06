# Using los-bootstrap

[← README](../README.md) · [Install](INSTALL.md) · [Usage](USAGE.md) · [Features](FEATURES.md)

Every capability is a subcommand of `los-bootstrap`. Run it with no
arguments for the interactive wizard, or call subcommands directly as
below. What each mode checks and why is in [FEATURES.md](FEATURES.md).

## Flashing a ROM (Phase 8)

```bash
# 0. Before anything destructive, read the pre-flash backup guidance
los-bootstrap flash backup

# 1. Check what state your device is in and identify the manufacturer
los-bootstrap flash status

# 2. Get the full bootloader unlock guide for your device (with live pre-checks)
los-bootstrap flash prepare

# 3. Verify your ROM zip targets the right device before flashing
los-bootstrap flash verify ~/Downloads/lineage-21-*.zip

# 4. Preview the flash sequence without running anything
los-bootstrap flash run ~/Downloads/lineage-21-*.zip --recovery ~/Downloads/recovery.img --dry-run

# 5. Execute the flash (destructive steps require --confirm)
los-bootstrap flash run ~/Downloads/lineage-21-*.zip --recovery ~/Downloads/recovery.img --confirm

# 6. After the first boot: verify the install, then track updates
los-bootstrap flash check
los-bootstrap flash update
```

## After the ROM is installed

Plug in your phone or tablet, enable USB debugging, accept the RSA
prompt, then:

```bash
los-bootstrap                    # launch the interactive guided wizard
```

Or use individual subcommands directly:

```bash
los-bootstrap devices            # list connected devices
los-bootstrap info               # device, ROM, build, security patch
los-bootstrap audit              # privacy/degoogle audit
los-bootstrap report             # full report (info + audit)
los-bootstrap report --json      # machine-readable
los-bootstrap recommend          # non-binding bootstrap suggestions

los-bootstrap profiles list                       # list bundled profiles
los-bootstrap plan    --profile privacy-default   # dry-run a profile
los-bootstrap apply   --profile privacy-default --confirm

los-bootstrap harden                              # lockdown report with why + tradeoff
los-bootstrap harden --interactive                # walk through findings, show fix commands
los-bootstrap harden --interactive --confirm      # walk through and apply fixes via adb
los-bootstrap harden --root                       # add SELinux check (needs su access)

los-bootstrap location doctor                     # diagnose the location stack on device
los-bootstrap location compat                     # app location compatibility matrix

los-bootstrap integrity doctor                    # why do apps block this custom ROM?
los-bootstrap integrity compat                    # German gov/banking app compatibility
los-bootstrap integrity guide                     # alternatives-first workaround guidance
los-bootstrap integrity install --list            # known spoofing modules for --fetch
los-bootstrap integrity install mod.zip --root --confirm  # install a spoofing module

los-bootstrap camera list-profiles                # list known GCam port profiles
los-bootstrap camera show panther                 # full port details + XML config path

los-bootstrap flash update                        # is my installed build current?
los-bootstrap flash check                         # post-flash first-boot verification
los-bootstrap flash backup                        # pre-flash backup guidance (no device)
```

If you have more than one device connected, pass `--serial <id>`.
The `camera`, `location compat`, `integrity compat`, `integrity guide`, `flash prepare`, `flash download <codename>`, and `flash backup` commands work without a device.

## Exit codes and output

Useful for scripting `los-bootstrap` in CI or shell pipelines:

| Code | Meaning |
|------|---------|
| 0    | Success — and for checks (`audit`, `report`, `harden`, `location doctor`, `flash verify`, `flash check`, `flash update`): nothing needs attention |
| 1    | Runtime failure (adb/fastboot/network error) |
| 2    | Usage error: bad flags, missing file, unknown profile |
| 3    | Checks ran fine but found issues that need attention |

For `flash check`, exit 3 means a check actually failed. Warnings (for
example real Play Services on a build you expected to be degoogled) are
printed in the report but do not change the exit code.

Report output is colorized when stdout is a terminal; set `NO_COLOR=1`
to disable or `FORCE_COLOR=1` to force it (e.g. when piping to `less -R`).
