"""Tests for the camera / GCam port profiles module."""

from __future__ import annotations

import pytest

from los_bootstrap.camera import (
    CAMERA_PROFILES,
    CameraPort,
    CameraProfile,
    XmlConfig,
    find_camera_profile,
    render_profile,
    render_profile_list,
)
from los_bootstrap.camera.profiles import CAMERA_PROFILES as _PROFILES_DIRECT


# ── Static profile data integrity ─────────────────────────────────────────────

def test_camera_profiles_non_empty():
    assert len(CAMERA_PROFILES) >= 3, "exit criteria: at least 3 device profiles"


def test_all_profiles_have_codename_and_display_name():
    for p in CAMERA_PROFILES:
        assert p.codename, f"profile {p!r} missing codename"
        assert p.display_name, f"profile {p!r} missing display_name"


def test_all_profiles_have_at_least_one_port():
    for p in CAMERA_PROFILES:
        assert len(p.ports) >= 1, f"{p.codename} must have at least one port"


def test_all_ports_have_required_fields():
    for p in CAMERA_PROFILES:
        for port in p.ports:
            assert port.name, f"{p.codename}/{port!r} missing name"
            assert port.package, f"{p.codename}/{port.name} missing package"
            assert port.source_hint, f"{p.codename}/{port.name} missing source_hint"
            assert port.notes, f"{p.codename}/{port.name} missing notes"


def test_verified_ports_have_xml_configs():
    for p in CAMERA_PROFILES:
        for port in p.ports:
            if port.verified:
                assert port.xml_configs, (
                    f"{p.codename}/{port.name} is verified but has no XML configs"
                )


def test_xml_configs_have_required_fields():
    for p in CAMERA_PROFILES:
        for port in p.ports:
            for xml in port.xml_configs:
                assert xml.filename, f"{p.codename}/{port.name} xml missing filename"
                assert xml.device_path, f"{p.codename}/{port.name} xml missing device_path"
                assert xml.description, f"{p.codename}/{port.name} xml missing description"
                assert xml.apply_hint, f"{p.codename}/{port.name} xml missing apply_hint"


def test_xml_device_paths_end_with_slash():
    for p in CAMERA_PROFILES:
        for port in p.ports:
            for xml in port.xml_configs:
                assert xml.device_path.endswith("/"), (
                    f"{p.codename}/{port.name} xml device_path should end with '/'"
                )


def test_no_duplicate_codenames():
    codenames = [p.codename.lower() for p in CAMERA_PROFILES]
    assert len(codenames) == len(set(codenames)), "duplicate codenames in CAMERA_PROFILES"


def test_known_devices_present():
    codenames = {p.codename.lower() for p in CAMERA_PROFILES}
    assert "panther" in codenames, "Pixel 7 (panther) expected in profiles"
    assert "oriole" in codenames, "Pixel 6 (oriole) expected in profiles"
    assert "sunny" in codenames, "Redmi Note 10 (sunny) expected in profiles"


def test_profiles_exported_from_package():
    assert _PROFILES_DIRECT is CAMERA_PROFILES


# ── find_camera_profile ────────────────────────────────────────────────────────

def test_find_profile_exact_match():
    profile = find_camera_profile("panther")
    assert profile is not None
    assert profile.codename == "panther"


def test_find_profile_case_insensitive():
    assert find_camera_profile("PANTHER") is not None
    assert find_camera_profile("Panther") is not None


def test_find_profile_unknown_returns_none():
    assert find_camera_profile("nonexistent_device_xyz") is None


def test_find_profile_fp4_uppercase_codename():
    profile = find_camera_profile("fp4")
    assert profile is not None
    assert profile.display_name == "Fairphone 4"


# ── render_profile_list ────────────────────────────────────────────────────────

def test_render_profile_list_header():
    text = render_profile_list()
    assert "Known GCam port profiles" in text


def test_render_profile_list_contains_all_codenames():
    text = render_profile_list()
    for p in CAMERA_PROFILES:
        assert p.codename in text, f"codename {p.codename!r} not in list output"


def test_render_profile_list_contains_port_names():
    text = render_profile_list()
    assert "LMC 8.4" in text
    assert "BSG" in text


def test_render_profile_list_contains_show_hint():
    text = render_profile_list()
    assert "camera show" in text


def test_render_profile_list_ends_with_newline():
    text = render_profile_list()
    assert text.endswith("\n")


# ── render_profile ─────────────────────────────────────────────────────────────

def test_render_profile_panther_contains_key_fields():
    profile = find_camera_profile("panther")
    assert profile is not None
    text = render_profile(profile)
    assert "Pixel 7" in text
    assert "panther" in text
    assert "LMC 8.4" in text
    assert "[verified]" in text
    assert "/sdcard/GCam/Config/" in text
    assert "adb push" in text


def test_render_profile_unverified_port_tagged():
    profile = find_camera_profile("sunny")
    assert profile is not None
    text = render_profile(profile)
    assert "[unverified]" in text


def test_render_profile_no_xml_says_none():
    profile = find_camera_profile("sunny")
    assert profile is not None
    text = render_profile(profile)
    assert "none" in text.lower()


def test_render_profile_ends_with_newline():
    profile = find_camera_profile("panther")
    assert profile is not None
    assert render_profile(profile).endswith("\n")


def test_render_profile_multiple_ports_all_shown():
    profile = find_camera_profile("sunny")
    assert profile is not None
    text = render_profile(profile)
    assert "BSG 9.3" in text
    assert "LMC 8.4" in text
    assert "Port 1" in text
    assert "Port 2" in text


# ── Model constructors ─────────────────────────────────────────────────────────

def test_camera_profile_frozen():
    p = CameraProfile(codename="test", display_name="Test", ports=())
    with pytest.raises((AttributeError, TypeError)):
        p.codename = "other"  # type: ignore[misc]


def test_xml_config_frozen():
    xml = XmlConfig(
        filename="foo.xml",
        device_path="/sdcard/GCam/Config/",
        description="desc",
        apply_hint="adb push foo.xml /sdcard/GCam/Config/",
    )
    with pytest.raises((AttributeError, TypeError)):
        xml.filename = "bar.xml"  # type: ignore[misc]
