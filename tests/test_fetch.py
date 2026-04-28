"""Tests for the APK downloader."""

from __future__ import annotations

import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from los_bootstrap.fetch import FetchError, download_apk


def _make_resp(body: bytes):
    """Context-manager mock that returns `body` on first read(), then b''."""
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.read.side_effect = [body, b""]
    return resp


def test_download_apk_direct_url(tmp_path):
    apk_content = b"fake apk data"
    with patch("urllib.request.urlopen", return_value=_make_resp(apk_content)):
        result = download_apk("https://example.com/test.apk", tmp_path)
    assert result == tmp_path / "test.apk"
    assert result.read_bytes() == apk_content


def test_download_apk_fdroid_scheme(tmp_path):
    api_body = json.dumps({"suggestedVersionCode": 1010059}).encode()
    apk_content = b"fake apk bytes"
    responses = [_make_resp(api_body), _make_resp(apk_content)]
    with patch("urllib.request.urlopen", side_effect=responses):
        result = download_apk("fdroid://org.fdroid.fdroid", tmp_path)
    assert result.name == "org.fdroid.fdroid_1010059.apk"
    assert result.read_bytes() == apk_content


def test_download_apk_cache_hit(tmp_path):
    existing = tmp_path / "test.apk"
    existing.write_bytes(b"cached content")
    with patch("urllib.request.urlopen") as mock_open:
        result = download_apk("https://example.com/test.apk", tmp_path)
        mock_open.assert_not_called()
    assert result == existing


def test_download_apk_fetch_error_on_http_failure(tmp_path):
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None),
    ):
        with pytest.raises(FetchError, match="HTTP 404"):
            download_apk("https://example.com/missing.apk", tmp_path)


def test_download_apk_fdroid_api_error(tmp_path):
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError("url", 500, "Server Error", {}, None),
    ):
        with pytest.raises(FetchError, match="F-Droid API returned 500"):
            download_apk("fdroid://com.example.app", tmp_path)


def test_download_apk_fdroid_missing_version_code(tmp_path):
    api_body = json.dumps({"packageName": "com.example.app"}).encode()
    with patch("urllib.request.urlopen", return_value=_make_resp(api_body)):
        with pytest.raises(FetchError, match="suggestedVersionCode"):
            download_apk("fdroid://com.example.app", tmp_path)
