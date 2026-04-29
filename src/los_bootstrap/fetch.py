"""Download APKs from declared URLs or via the F-Droid package index."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

FDROID_API = "https://f-droid.org/api/v1/packages/{pkg}"
FDROID_REPO = "https://f-droid.org/repo/{pkg}_{code}.apk"
GITHUB_API = "https://api.github.com/repos/{repo}/releases/latest"


class FetchError(Exception):
    pass


def download_apk(url: str, dest_dir: Path) -> Path:
    """Download an APK to `dest_dir` and return the local path.

    Supported URL schemes:
    - ``fdroid://<package-id>`` — resolved via the F-Droid API
    - ``github://<owner>/<repo>`` — resolved to the latest .apk release asset
    - plain HTTPS — downloaded directly

    Files already present in `dest_dir` are returned immediately (cache hit).
    """
    if url.startswith("fdroid://"):
        url = _resolve_fdroid(url[9:])
    elif url.startswith("github://"):
        url = _resolve_github(url[9:])
    filename = url.rsplit("/", 1)[-1].split("?")[0]
    dest = dest_dir / filename
    if dest.exists():
        return dest
    _stream(url, dest)
    return dest


def _resolve_github(repo: str) -> str:
    """Return the browser_download_url of the first .apk asset in the latest release."""
    api_url = GITHUB_API.format(repo=repo)
    try:
        req = urllib.request.Request(
            api_url,
            headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise FetchError(f"GitHub API returned {exc.code} for {repo}") from exc
    except OSError as exc:
        raise FetchError(f"network error querying GitHub: {exc}") from exc

    apk_assets = [a for a in data.get("assets", []) if a.get("name", "").endswith(".apk")]
    if not apk_assets:
        raise FetchError(f"no .apk asset found in latest release of {repo}")
    return apk_assets[0]["browser_download_url"]


def _resolve_fdroid(package_id: str) -> str:
    api_url = FDROID_API.format(pkg=package_id)
    try:
        with urllib.request.urlopen(api_url, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise FetchError(f"F-Droid API returned {exc.code} for {package_id}") from exc
    except OSError as exc:
        raise FetchError(f"network error querying F-Droid: {exc}") from exc

    version_code = data.get("suggestedVersionCode")
    if not version_code:
        raise FetchError(f"F-Droid API missing suggestedVersionCode for {package_id}")
    return FDROID_REPO.format(pkg=package_id, code=version_code)


def _stream(url: str, dest: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            with dest.open("wb") as fh:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
    except urllib.error.HTTPError as exc:
        if dest.exists():
            dest.unlink()
        raise FetchError(f"HTTP {exc.code} downloading {url}") from exc
    except OSError as exc:
        if dest.exists():
            dest.unlink()
        raise FetchError(f"network error downloading {url}: {exc}") from exc
