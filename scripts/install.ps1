<#
.SYNOPSIS
    los-bootstrap one-line installer for Windows.

.DESCRIPTION
    Detects winget or scoop, installs Python and android-platform-tools,
    then runs `pipx install "los-bootstrap[wizard]"`.

    What this does NOT do:
      - Bundle adb. We use whatever winget/scoop ships.
      - Install fastboot or heimdall (only needed for flash run / Samsung).
      - Modify any system config beyond installing those packages.

.PARAMETER DryRun
    Print the commands that would run, without executing them.

.PARAMETER Yes
    Skip the confirmation prompt.

.EXAMPLE
    irm https://raw.githubusercontent.com/richardkfm/los-bootstrap/main/scripts/install.ps1 | iex

.EXAMPLE
    .\install.ps1 -DryRun
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

function Write-Log {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Warn {
    param([string]$Message)
    Write-Host "!!  $Message" -ForegroundColor Yellow
}

function Invoke-Step {
    param([string]$Command)
    Write-Host "    $ $Command" -ForegroundColor DarkGray
    if ($DryRun) { return }
    & cmd /c $Command
    if ($LASTEXITCODE -ne 0) {
        throw "command failed (exit $LASTEXITCODE): $Command"
    }
}

function Confirm-Or-Exit {
    param([string]$Prompt)
    if ($Yes -or $DryRun) { return }
    $answer = Read-Host "$Prompt [y/N]"
    if ($answer -notmatch '^(y|Y|yes|YES)$') {
        Write-Warn "aborted by user"
        exit 1
    }
}

# Detect package manager
$PM = $null
if (Get-Command winget -ErrorAction SilentlyContinue) {
    $PM = 'winget'
} elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
    $PM = 'scoop'
} else {
    Write-Warn "neither winget nor scoop is installed."
    Write-Warn "winget ships with Windows 11 and modern Windows 10 (App Installer)."
    Write-Warn "Install it from https://aka.ms/getwinget, or install scoop from https://scoop.sh, then re-run."
    exit 1
}

Write-Log "detected package manager: $PM"

Write-Log "los-bootstrap installer plan"
Write-Host "    1. install Python via $PM (skipped if already present)"
Write-Host "    2. install android-platform-tools via $PM (provides adb)"
Write-Host "    3. pipx ensurepath"
Write-Host "    4. pipx install `"los-bootstrap[wizard]`""
Write-Host ""
Write-Host "    fastboot and heimdall are NOT installed by default. The flash"
Write-Host "    subcommand will tell you when you need them."
Write-Host ""

if ($DryRun) {
    Write-Log "dry-run mode -- printing commands without executing"
}

Confirm-Or-Exit "proceed?"

switch ($PM) {
    'winget' {
        # --silent + --accept-* avoids interactive prompts; --exact pins the id.
        # Python.Python.3.12 is the LTS-ish current line; bump as needed.
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            Invoke-Step "winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements --silent"
        } else {
            Write-Log "python already on PATH, skipping install"
        }
        Invoke-Step "winget install --id Google.PlatformTools -e --accept-package-agreements --accept-source-agreements --silent"
    }
    'scoop' {
        if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
            Invoke-Step "scoop install python"
        } else {
            Write-Log "python already on PATH, skipping install"
        }
        Invoke-Step "scoop install adb"
    }
}

# pipx itself is not in winget/scoop reliably, so install via pip.
Invoke-Step "python -m pip install --user --upgrade pipx"
Invoke-Step "python -m pipx ensurepath"
Invoke-Step "python -m pipx install --force `"los-bootstrap[wizard]`""

Write-Log "done."
Write-Host ""
Write-Host "    If 'los-bootstrap' isn't found yet, close this PowerShell window"
Write-Host "    and open a new one so the updated PATH takes effect."
Write-Host ""
Write-Host "    Next steps:"
Write-Host "      los-bootstrap version"
Write-Host "      los-bootstrap                    # interactive wizard"
Write-Host "      los-bootstrap audit              # privacy/degoogle audit"
