"""Install a Magisk / KernelSU / APatch module (mutating; --root --confirm gated).

This is the only mutating module in the `integrity` package, and the only place
in the whole tool that installs a root module. It exists to let a user keep a
working phone in service by spoofing a Play Integrity verdict on their own
device — never presented as making the phone safer.

Guardrails enforced here (not just in the CLI):
- refuses to do anything without `root=True`
- refuses a zip that has no `module.prop`
- makes no network call unless a `--fetch` name is given
- prints the SHA-256 and `module.prop` details, and the three mandatory
  warnings, before every install — whether or not `--confirm` was passed
- only `--confirm` performs the push + install; otherwise it previews and stops

Keyboxes are never fetched, shipped, or explained (Phase 12 non-goal).
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO

from ..adb import Adb, AdbCommandError
from .. import fetch
from ..fetch import FetchError
from .guide import WARNINGS
from .modules import ModuleSource, find_module_source

REMOTE_TMP = "/data/local/tmp/los-bootstrap-module.zip"

# label, probe binary, install-command template ({zip} is the on-device path).
ROOT_METHODS: tuple[tuple[str, str, str], ...] = (
    ("Magisk", "magisk", "magisk --install-module {zip}"),
    ("KernelSU", "ksud", "ksud module install {zip}"),
    ("APatch", "apd", "apd module install {zip}"),
)


@dataclass(frozen=True)
class ModuleInfo:
    module_id: str
    name: str
    version: str
    version_code: str
    author: str


@dataclass(frozen=True)
class InstallOutcome:
    status: str  # "installed" | "previewed" | "refused" | "error"
    detail: str = ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_module_prop(zip_path: Path) -> Optional[ModuleInfo]:
    """Parse module.prop from a Magisk-style module zip, or None if absent/invalid."""
    if not zipfile.is_zipfile(zip_path):
        return None
    try:
        with zipfile.ZipFile(zip_path) as zf:
            if "module.prop" not in zf.namelist():
                return None
            raw = zf.read("module.prop").decode("utf-8", "replace")
    except (OSError, zipfile.BadZipFile):
        return None
    props: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value.strip()
    if "id" not in props:
        return None
    return ModuleInfo(
        module_id=props.get("id", ""),
        name=props.get("name", ""),
        version=props.get("version", ""),
        version_code=props.get("versionCode", ""),
        author=props.get("author", ""),
    )


def detect_root_method(adb: Adb) -> Optional[tuple[str, str]]:
    """Return (label, install-command template) for the device's root manager, or None."""
    for label, probe, template in ROOT_METHODS:
        try:
            found = adb.shell(f"su -c 'command -v {probe}'").strip()
        except AdbCommandError:
            continue
        if found:
            return label, template
    return None


def _print_warnings(out: TextIO) -> None:
    out.write("Before you install a spoofing module, read these:\n")
    for title, body in WARNINGS:
        out.write(f"\n  ⚠  {title}: {body}\n")
    out.write("\n")


def run_install(
    adb: Adb,
    *,
    module_path: Optional[str],
    fetch_name: Optional[str],
    root: bool,
    confirm: bool,
    out: TextIO = sys.stdout,
    cache_dir: Optional[Path] = None,
) -> InstallOutcome:
    """Preview or install a root module. Returns an InstallOutcome.

    `--confirm` is required to actually push and install; without it this
    previews (metadata, SHA-256, warnings) and stops. `root` must be True.
    Network is used only when `fetch_name` is set.
    """
    if not root:
        out.write(
            "error: `integrity install` installs a root module and requires --root.\n"
            "Re-run with --root once you understand it needs an already-rooted device.\n"
        )
        return InstallOutcome("refused", "missing --root")

    if bool(module_path) == bool(fetch_name):
        out.write(
            "error: pass exactly one of a local <module.zip> or --fetch <name>.\n"
            "List known modules with `los-bootstrap integrity install --list`.\n"
        )
        return InstallOutcome("refused", "need exactly one source")

    origin: str
    if fetch_name:
        source = find_module_source(fetch_name)
        if source is None:
            out.write(f"error: unknown module {fetch_name!r}. See --list.\n")
            return InstallOutcome("refused", "unknown module")
        try:
            zip_path, origin = _fetch_module(source, cache_dir, out)
        except FetchError as exc:
            out.write(f"error: {exc}\n")
            return InstallOutcome("error", str(exc))
    else:
        assert module_path is not None
        zip_path = Path(module_path)
        if not zip_path.is_file():
            out.write(f"error: file not found: {zip_path}\n")
            return InstallOutcome("refused", "file not found")
        origin = f"local file {zip_path}"

    info = read_module_prop(zip_path)
    if info is None:
        out.write(
            f"error: {zip_path} is not a valid module — no readable module.prop.\n"
            "Refusing to install. A Magisk/KernelSU module zip always has one.\n"
        )
        return InstallOutcome("refused", "no module.prop")

    digest = sha256_file(zip_path)
    method = detect_root_method(adb)

    out.write("Module to install\n")
    out.write("─────────────────\n")
    out.write(f"  source   : {origin}\n")
    out.write(f"  id       : {info.module_id}\n")
    out.write(f"  name     : {info.name or '(unnamed)'}\n")
    out.write(f"  version  : {info.version} ({info.version_code})\n")
    out.write(f"  author   : {info.author or '(unknown)'}\n")
    out.write(f"  sha256   : {digest}\n")
    out.write(f"  root mgr : {method[0] if method else 'none detected'}\n")
    out.write("\n")

    _print_warnings(out)

    if not confirm:
        out.write(
            "Preview only — nothing was installed. Re-run with --confirm to push and\n"
            "install this module, then reboot for it to take effect.\n"
        )
        return InstallOutcome("previewed", info.module_id)

    if method is None:
        out.write(
            "error: no Magisk, KernelSU, or APatch binary reachable via `su`.\n"
            "The device must already be rooted; this tool does not root it.\n"
            "See `los-bootstrap integrity guide` step 5.\n"
        )
        return InstallOutcome("error", "no root method")

    label, template = method
    out.write(f"Installing via {label}…\n")
    try:
        adb.push(str(zip_path), REMOTE_TMP)
        command = template.format(zip=REMOTE_TMP)
        out.write(f"  run    : su -c '{command}'\n")
        result = adb.shell(f"su -c '{command}'")
        if result.strip():
            out.write("  " + result.strip().replace("\n", "\n  ") + "\n")
    except AdbCommandError as exc:
        out.write(f"error: install failed: {exc}\n")
        _cleanup_remote(adb)
        return InstallOutcome("error", str(exc))

    _cleanup_remote(adb)
    out.write("\nInstalled. Reboot the device for the module to take effect.\n")
    return InstallOutcome("installed", info.module_id)


def _fetch_module(
    source: ModuleSource, cache_dir: Optional[Path], out: TextIO
) -> tuple[Path, str]:
    dest = cache_dir or Path(tempfile.mkdtemp())
    url, name, tag = fetch.resolve_github_asset(source.repo, suffix=source.asset_suffix)
    out.write(f"Fetching {source.repo} release {tag or '(latest)'}: {name}\n")
    path = fetch.download_url(url, dest)
    origin = f"{source.repo} @ {tag or 'latest'} ({name})"
    return path, origin


def _cleanup_remote(adb: Adb) -> None:
    try:
        adb.shell(f"rm -f {REMOTE_TMP}")
    except AdbCommandError:
        pass
