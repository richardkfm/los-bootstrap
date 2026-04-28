"""Tests for the YAML profile loader and bundled profiles."""

from __future__ import annotations

from pathlib import Path

import pytest

from los_bootstrap.profiles import (
    AppEntry,
    ProfileError,
    SettingEntry,
    bundled_profiles_dir,
    find_profile,
    list_bundled_profiles,
    load_profile,
)


def test_bundled_profiles_present():
    names = {p.name for p in list_bundled_profiles()}
    assert {"minimal", "privacy-default", "messaging-light"} <= names


def test_loads_bundled_privacy_default():
    p = load_profile(bundled_profiles_dir() / "privacy-default.yml")
    assert p.name == "privacy-default"
    ids = [a.id for a in p.apps]
    assert "org.fdroid.fdroid" in ids
    fdroid = next(a for a in p.apps if a.id == "org.fdroid.fdroid")
    assert fdroid.source == "sideload"
    assert fdroid.apk == "F-Droid.apk"
    namespaces = {entry.namespace for entry in p.settings}
    assert "global" in namespaces
    # Every setting should reference one of the allowed namespaces.
    assert namespaces <= {"global", "secure", "system"}


def test_string_app_entry_is_shorthand_for_fdroid(tmp_path):
    f = tmp_path / "p.yml"
    f.write_text(
        "name: shorthand\n"
        "description: shorthand test\n"
        "apps:\n"
        "  - net.osmand.plus\n",
        encoding="utf-8",
    )
    p = load_profile(f)
    assert p.apps == (AppEntry(id="net.osmand.plus", source="fdroid"),)


def test_settings_entry_round_trip(tmp_path):
    f = tmp_path / "p.yml"
    f.write_text(
        "name: s\n"
        "description: ''\n"
        "settings:\n"
        "  - namespace: global\n"
        "    key: private_dns_mode\n"
        "    value: hostname\n"
        "    note: enable DoT\n",
        encoding="utf-8",
    )
    p = load_profile(f)
    assert p.settings == (
        SettingEntry(
            namespace="global",
            key="private_dns_mode",
            value="hostname",
            note="enable DoT",
        ),
    )


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


def test_rejects_unknown_app_source(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        "name: x\n"
        "description: ''\n"
        "apps:\n"
        "  - id: com.example.app\n"
        "    source: bittorrent\n",
        encoding="utf-8",
    )
    with pytest.raises(ProfileError, match="unknown source"):
        load_profile(bad)


def test_sideload_requires_apk(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        "name: x\n"
        "description: ''\n"
        "apps:\n"
        "  - id: com.example.app\n"
        "    source: sideload\n",
        encoding="utf-8",
    )
    with pytest.raises(ProfileError, match="apk"):
        load_profile(bad)


def test_rejects_unknown_settings_namespace(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text(
        "name: x\n"
        "description: ''\n"
        "settings:\n"
        "  - namespace: rootonly\n"
        "    key: foo\n"
        "    value: bar\n",
        encoding="utf-8",
    )
    with pytest.raises(ProfileError, match="namespace"):
        load_profile(bad)


def test_find_profile_resolves_bundled_by_name():
    p = find_profile("minimal")
    assert p.name == "minimal"


def test_find_profile_resolves_path(tmp_path):
    f = tmp_path / "custom.yml"
    f.write_text("name: custom\ndescription: ''\n", encoding="utf-8")
    p = find_profile(str(f))
    assert p.name == "custom"


def test_find_profile_searches_extra_dirs(tmp_path):
    f = tmp_path / "weird.yml"
    f.write_text("name: weird\ndescription: ''\n", encoding="utf-8")
    p = find_profile("weird", extra_dirs=[tmp_path])
    assert p.name == "weird"


def test_find_profile_missing_raises():
    with pytest.raises(ProfileError, match="not found"):
        find_profile("does-not-exist-anywhere")
