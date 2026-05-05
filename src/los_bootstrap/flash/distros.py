"""ROM download links and LineageOS build lookup for the flash assistant.

Provides:

- ``lineage_device_url(codename)`` — the human-browsable LOS download page.
- ``lookup_lineage_build(codename)`` — query the LOS public JSON API and
  return the latest build's filename, URL, size and SHA-256.
- ``alt_distro_links(codename)`` — page URLs for sister distros (DivestOS,
  /e/OS, LineageOS for microG, CalyxOS, GrapheneOS, iodéOS).
- ``download_lineage_zip(build, dest_dir)`` — stream the zip and verify the
  SHA-256 reported by the API.

Network access only happens when the user explicitly invokes
``los-bootstrap flash download``; this module is otherwise inert.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

LOS_API = "https://download.lineageos.org/api/v2/devices/{codename}/builds"
LOS_PAGE = "https://download.lineageos.org/devices/{codename}/builds"

HttpOpener = Callable[[str, float], "urllib.request.addinfourl"]


class DistroFetchError(Exception):
    """Raised when the LOS API is unreachable or returns an unusable payload."""


@dataclass(frozen=True)
class LineageBuild:
    codename: str
    filename: str
    url: str
    size: int
    sha256: str
    version: str          # e.g. "21" or "22.0"
    datetime: int         # epoch seconds
    build_type: str       # e.g. "nightly"


# ---------------------------------------------------------------------------
# Sister-distro page links
# ---------------------------------------------------------------------------

# For each distro we know whether the page is per-codename or a single global
# install page. Codename substitutions happen below — distros without a
# stable per-codename URL get the closest available landing page instead.
_ALT_DISTROS: list[tuple[str, str, bool]] = [
    # (display name, URL template, is_codename_based)
    ("LineageOS for microG", "https://download.lineage.microg.org/{codename}/", True),
    ("/e/OS",                "https://images.ecloud.global/stable/{codename}/", True),
    ("DivestOS",             "https://divestos.org/index.php?page=devices",     False),
    ("CalyxOS",              "https://calyxos.org/install/devices/",            False),
    ("GrapheneOS",           "https://grapheneos.org/install/",                 False),
    ("iodéOS",               "https://iode.tech/en/smartphones-iode/",          False),
]


def lineage_device_url(codename: str) -> str:
    """Return the human-browsable LineageOS downloads page for a codename."""
    return LOS_PAGE.format(codename=codename)


def alt_distro_links(codename: str) -> list[tuple[str, str]]:
    """Return [(distro name, URL)] pointing to the closest available page.

    Distros without a stable per-codename URL fall back to their main install
    landing page; users will need to look up their device there.
    """
    out: list[tuple[str, str]] = []
    for name, template, per_codename in _ALT_DISTROS:
        url = template.format(codename=codename) if per_codename and codename else template
        out.append((name, url))
    return out


# ---------------------------------------------------------------------------
# LineageOS JSON API
# ---------------------------------------------------------------------------

def lookup_lineage_build(
    codename: str,
    *,
    opener: Optional[HttpOpener] = None,
    timeout: float = 15.0,
) -> Optional[LineageBuild]:
    """Return the latest LineageOS build for ``codename``, or ``None``.

    Returns ``None`` when the API responds 404 (device not supported) or the
    list is empty. Raises :class:`DistroFetchError` on network or parse errors.

    The ``opener`` parameter is for testing; production callers should leave
    it at the default and let the function use ``urllib.request.urlopen``.
    """
    if not codename:
        raise DistroFetchError("codename is empty")

    url = LOS_API.format(codename=codename)
    open_fn = opener or _default_opener
    try:
        with open_fn(url, timeout) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise DistroFetchError(f"LineageOS API returned HTTP {exc.code} for {codename}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise DistroFetchError(f"network error querying LineageOS API: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DistroFetchError(f"LineageOS API returned non-JSON payload: {exc}") from exc

    return _pick_latest_build(codename, data)


def _default_opener(url: str, timeout: float) -> "urllib.request.addinfourl":
    req = urllib.request.Request(url, headers={"User-Agent": "los-bootstrap"})
    return urllib.request.urlopen(req, timeout=timeout)


def _pick_latest_build(codename: str, data: object) -> Optional[LineageBuild]:
    """Pick the most recent nightly build from a LOS API v2 response.

    The v2 response is a JSON array of build objects; each has a ``files``
    list. The first file is the ROM zip itself (the others are images and
    boot artefacts). We pick the build with the highest ``datetime``.
    """
    if not isinstance(data, list) or not data:
        return None

    builds = [b for b in data if isinstance(b, dict)]
    if not builds:
        return None

    builds.sort(key=lambda b: int(b.get("datetime", 0) or 0), reverse=True)
    for build in builds:
        rom = _extract_rom_file(build)
        if rom is None:
            continue
        filename, file_url, size, sha256 = rom
        return LineageBuild(
            codename=codename,
            filename=filename,
            url=file_url,
            size=int(size or 0),
            sha256=sha256 or "",
            version=str(build.get("version") or ""),
            datetime=int(build.get("datetime") or 0),
            build_type=str(build.get("build_type") or build.get("type") or ""),
        )
    return None


def _extract_rom_file(build: dict) -> Optional[tuple[str, str, int, str]]:
    """Return (filename, url, size, sha256) for the ROM zip in this build.

    The v2 schema lists files under ``files``; the ROM zip is the entry whose
    filename ends in ``.zip``. Older payloads sometimes flattened these
    fields onto the build object itself, so we tolerate both shapes.
    """
    files = build.get("files")
    if isinstance(files, list):
        for entry in files:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("filename") or "")
            if name.endswith(".zip"):
                return (
                    name,
                    str(entry.get("url") or ""),
                    int(entry.get("size") or 0),
                    str(entry.get("sha256") or ""),
                )
    name = str(build.get("filename") or "")
    if name.endswith(".zip"):
        return (
            name,
            str(build.get("url") or ""),
            int(build.get("size") or 0),
            str(build.get("sha256") or ""),
        )
    return None


# ---------------------------------------------------------------------------
# Streaming download with SHA-256 verification
# ---------------------------------------------------------------------------

def download_lineage_zip(
    build: LineageBuild,
    dest_dir: Path,
    *,
    opener: Optional[HttpOpener] = None,
    timeout: float = 60.0,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Stream ``build`` to ``dest_dir`` and verify its SHA-256.

    Returns the local path to the downloaded zip. Reuses an existing file in
    ``dest_dir`` if its SHA-256 matches the build hash; otherwise re-downloads.
    Raises :class:`DistroFetchError` on transport errors or hash mismatch.
    """
    if not build.url:
        raise DistroFetchError("build has no download URL")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / build.filename

    if dest.exists() and build.sha256 and _sha256_of(dest) == build.sha256.lower():
        return dest

    open_fn = opener or _default_opener
    h = hashlib.sha256()
    bytes_read = 0
    try:
        with open_fn(build.url, timeout) as resp:
            with dest.open("wb") as fh:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
                    h.update(chunk)
                    bytes_read += len(chunk)
                    if progress is not None:
                        progress(bytes_read, build.size)
    except urllib.error.HTTPError as exc:
        if dest.exists():
            dest.unlink()
        raise DistroFetchError(f"HTTP {exc.code} downloading {build.url}") from exc
    except (urllib.error.URLError, OSError) as exc:
        if dest.exists():
            dest.unlink()
        raise DistroFetchError(f"network error downloading {build.url}: {exc}") from exc

    if build.sha256 and h.hexdigest() != build.sha256.lower():
        dest.unlink(missing_ok=True)
        raise DistroFetchError(
            f"SHA-256 mismatch for {build.filename}: "
            f"expected {build.sha256}, got {h.hexdigest()}"
        )
    return dest


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
