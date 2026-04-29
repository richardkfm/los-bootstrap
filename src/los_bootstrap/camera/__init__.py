"""Camera / GCam port profiles — Phase 5.

Public surface:
    CAMERA_PROFILES             — tuple of CameraProfile
    find_camera_profile(str)    -> CameraProfile | None
    render_profile_list()       -> str
    render_profile(profile)     -> str
"""

from __future__ import annotations

from typing import Optional

from .models import CameraPort, CameraProfile, XmlConfig
from .profiles import CAMERA_PROFILES
from .report import render_profile, render_profile_list

__all__ = [
    "CAMERA_PROFILES",
    "CameraPort",
    "CameraProfile",
    "XmlConfig",
    "find_camera_profile",
    "render_profile",
    "render_profile_list",
]


def find_camera_profile(codename: str) -> Optional[CameraProfile]:
    """Return the camera profile for the given device codename, or None."""
    codename_lower = codename.lower()
    for profile in CAMERA_PROFILES:
        if profile.codename.lower() == codename_lower:
            return profile
    return None
