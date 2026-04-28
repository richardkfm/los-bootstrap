"""Tests for the YAML profile loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from los_bootstrap.profiles import ProfileError, load_profile


def test_loads_bundled_privacy_default():
    repo_root = Path(__file__).resolve().parents[1]
    p = load_profile(repo_root / "profiles" / "privacy-default.yml")
    assert p.name == "privacy-default"
    assert "org.fdroid.fdroid" in p.apps
    namespaces = {entry[0] for entry in p.settings}
    assert "global" in namespaces


def test_rejects_missing_name(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("description: nope\n", encoding="utf-8")
    with pytest.raises(ProfileError):
        load_profile(bad)


def test_rejects_non_mapping_top_level(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ProfileError):
        load_profile(bad)
