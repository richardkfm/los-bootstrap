"""Tests for flash/distros.py — LineageOS API + sister-distro links.

No real network access — all HTTP IO is injected via the ``opener`` parameter.
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.error
from contextlib import contextmanager
from pathlib import Path

import pytest

from los_bootstrap.flash.distros import (
    DistroFetchError,
    LineageBuild,
    _pick_latest_build,
    alt_distro_links,
    download_lineage_zip,
    lineage_device_url,
    lookup_lineage_build,
)


# ---------------------------------------------------------------------------
# Fake HTTP openers
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body
        self._buf = io.BytesIO(body)

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            return self._buf.read()
        return self._buf.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._buf.close()


def _opener_returning(payload: bytes):
    def opener(url: str, timeout: float):
        return _FakeResponse(payload)
    return opener


def _opener_raising(exc: Exception):
    def opener(url: str, timeout: float):
        raise exc
    return opener


# ---------------------------------------------------------------------------
# lineage_device_url / alt_distro_links
# ---------------------------------------------------------------------------

def test_lineage_device_url_substitutes_codename():
    assert lineage_device_url("bluejay") == "https://download.lineageos.org/devices/bluejay/builds"


def test_alt_distro_links_includes_known_distros():
    links = dict(alt_distro_links("bluejay"))
    assert "/e/OS" in links
    assert "bluejay" in links["/e/OS"]
    assert "LineageOS for microG" in links
    assert "bluejay" in links["LineageOS for microG"]
    # Distros without per-codename URLs fall back to a landing page.
    assert "DivestOS" in links
    assert "bluejay" not in links["DivestOS"]
    assert "GrapheneOS" in links
    assert "CalyxOS" in links


def test_alt_distro_links_handles_empty_codename():
    links = dict(alt_distro_links(""))
    # Per-codename templates render with empty codename (still a valid URL).
    assert "LineageOS for microG" in links


# ---------------------------------------------------------------------------
# _pick_latest_build — schema parsing
# ---------------------------------------------------------------------------

def _v2_build(datetime: int, filename: str, sha256: str = "deadbeef", size: int = 1024) -> dict:
    return {
        "datetime": datetime,
        "version": "21.0",
        "build_type": "nightly",
        "files": [
            {
                "filename": filename,
                "url": f"https://example.invalid/{filename}",
                "size": size,
                "sha256": sha256,
            }
        ],
    }


def test_pick_latest_build_returns_newest():
    data = [
        _v2_build(100, "lineage-21.0-old-bluejay.zip"),
        _v2_build(200, "lineage-21.0-new-bluejay.zip"),
        _v2_build(150, "lineage-21.0-mid-bluejay.zip"),
    ]
    build = _pick_latest_build("bluejay", data)
    assert build is not None
    assert build.filename == "lineage-21.0-new-bluejay.zip"
    assert build.datetime == 200
    assert build.size == 1024


def test_pick_latest_build_empty_list_returns_none():
    assert _pick_latest_build("bluejay", []) is None


def test_pick_latest_build_skips_non_dict_entries():
    data = ["not a dict", _v2_build(100, "lineage-21.0-bluejay.zip")]
    build = _pick_latest_build("bluejay", data)
    assert build is not None
    assert build.filename == "lineage-21.0-bluejay.zip"


def test_pick_latest_build_handles_flat_schema():
    data = [{
        "datetime": 100,
        "version": "21.0",
        "filename": "lineage-21.0-flat-bluejay.zip",
        "url": "https://example.invalid/flat.zip",
        "size": 999,
        "sha256": "cafebabe",
    }]
    build = _pick_latest_build("bluejay", data)
    assert build is not None
    assert build.filename == "lineage-21.0-flat-bluejay.zip"
    assert build.sha256 == "cafebabe"


def test_pick_latest_build_skips_builds_without_zip():
    data = [{
        "datetime": 100,
        "files": [{"filename": "boot.img", "url": "...", "size": 1, "sha256": ""}],
    }]
    assert _pick_latest_build("bluejay", data) is None


# ---------------------------------------------------------------------------
# lookup_lineage_build — opener-injected
# ---------------------------------------------------------------------------

def test_lookup_lineage_build_success():
    payload = json.dumps([_v2_build(200, "lineage-21.0-bluejay.zip", sha256="abcd")]).encode()
    build = lookup_lineage_build("bluejay", opener=_opener_returning(payload))
    assert build is not None
    assert build.filename == "lineage-21.0-bluejay.zip"
    assert build.sha256 == "abcd"
    assert build.codename == "bluejay"


def test_lookup_lineage_build_404_returns_none():
    err = urllib.error.HTTPError(
        url="https://example.invalid", code=404, msg="Not Found", hdrs=None, fp=None
    )
    assert lookup_lineage_build("nosuch", opener=_opener_raising(err)) is None


def test_lookup_lineage_build_other_http_error_raises():
    err = urllib.error.HTTPError(
        url="https://example.invalid", code=500, msg="Server Error", hdrs=None, fp=None
    )
    with pytest.raises(DistroFetchError) as exc_info:
        lookup_lineage_build("bluejay", opener=_opener_raising(err))
    assert "500" in str(exc_info.value)


def test_lookup_lineage_build_network_error_raises():
    with pytest.raises(DistroFetchError):
        lookup_lineage_build("bluejay", opener=_opener_raising(OSError("connection refused")))


def test_lookup_lineage_build_invalid_json_raises():
    with pytest.raises(DistroFetchError):
        lookup_lineage_build("bluejay", opener=_opener_returning(b"<html>nope</html>"))


def test_lookup_lineage_build_empty_codename_raises():
    with pytest.raises(DistroFetchError):
        lookup_lineage_build("", opener=_opener_returning(b"[]"))


def test_lookup_lineage_build_empty_array_returns_none():
    assert lookup_lineage_build("bluejay", opener=_opener_returning(b"[]")) is None


# ---------------------------------------------------------------------------
# download_lineage_zip — sha256 verify, cache hit, mismatch
# ---------------------------------------------------------------------------

def _build_for(content: bytes, filename: str = "lineage-21.0-bluejay.zip") -> LineageBuild:
    return LineageBuild(
        codename="bluejay",
        filename=filename,
        url=f"https://example.invalid/{filename}",
        size=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        version="21.0",
        datetime=200,
        build_type="nightly",
    )


def test_download_lineage_zip_writes_and_verifies(tmp_path: Path):
    content = b"FAKE LINEAGEOS ZIP CONTENT"
    build = _build_for(content)
    path = download_lineage_zip(build, tmp_path, opener=_opener_returning(content))
    assert path.read_bytes() == content
    assert path.parent == tmp_path
    assert path.name == build.filename


def test_download_lineage_zip_cache_hit_skips_download(tmp_path: Path):
    content = b"already on disk"
    build = _build_for(content)
    dest = tmp_path / build.filename
    dest.write_bytes(content)

    def opener(url, timeout):
        raise AssertionError("opener must not be called on cache hit")

    path = download_lineage_zip(build, tmp_path, opener=opener)
    assert path == dest


def test_download_lineage_zip_sha256_mismatch_deletes_partial(tmp_path: Path):
    content = b"correct content"
    build = _build_for(content)
    # Replace what the server returns with garbage so the SHA-256 won't match.
    bad_content = b"WRONG CONTENT WRONG CONTENT"
    with pytest.raises(DistroFetchError) as exc_info:
        download_lineage_zip(build, tmp_path, opener=_opener_returning(bad_content))
    assert "SHA-256 mismatch" in str(exc_info.value)
    assert not (tmp_path / build.filename).exists()


def test_download_lineage_zip_http_error_raises_and_cleans_up(tmp_path: Path):
    err = urllib.error.HTTPError(
        url="https://example.invalid", code=503, msg="Down", hdrs=None, fp=None
    )
    build = _build_for(b"x")
    with pytest.raises(DistroFetchError):
        download_lineage_zip(build, tmp_path, opener=_opener_raising(err))
    assert not (tmp_path / build.filename).exists()


def test_download_lineage_zip_progress_callback(tmp_path: Path):
    content = b"x" * 100
    build = _build_for(content)
    calls: list[tuple[int, int]] = []
    download_lineage_zip(
        build,
        tmp_path,
        opener=_opener_returning(content),
        progress=lambda r, t: calls.append((r, t)),
    )
    assert calls
    assert calls[-1][0] == len(content)
