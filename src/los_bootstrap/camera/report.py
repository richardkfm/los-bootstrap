"""Render GCam port camera profiles as text."""

from __future__ import annotations

from .models import CameraProfile
from .profiles import CAMERA_PROFILES


def render_profile_list() -> str:
    lines: list[str] = []
    lines.append("Known GCam port profiles")
    lines.append("------------------------")
    lines.append(f"  {'Codename':<16}  {'Device':<32}  Ports")
    lines.append(f"  {'-' * 16}  {'-' * 32}  {'-' * 5}")

    for profile in CAMERA_PROFILES:
        port_names = ", ".join(p.name for p in profile.ports)
        lines.append(f"  {profile.codename:<16}  {profile.display_name:<32}  {port_names}")

    lines.append("")
    lines.append("Use `camera show <codename>` for full details and XML config paths.")
    return "\n".join(lines) + "\n"


def render_profile(profile: CameraProfile) -> str:
    lines: list[str] = []
    lines.append(f"Camera profile: {profile.display_name} ({profile.codename})")
    lines.append("-" * 60)

    if profile.notes:
        lines.append(f"  {profile.notes}")
        lines.append("")

    for i, port in enumerate(profile.ports, 1):
        tag = "[verified]" if port.verified else "[unverified]"
        lines.append(f"  Port {i}: {port.name}  {tag}")
        lines.append(f"    Package : {port.package}")
        lines.append(f"    Source  : {port.source_hint}")
        if port.notes:
            lines.append(f"    Notes   : {port.notes}")

        if port.xml_configs:
            lines.append(f"    XML configs ({len(port.xml_configs)}):")
            for xml in port.xml_configs:
                lines.append(f"      • {xml.filename}")
                lines.append(f"        Path    : {xml.device_path}")
                lines.append(f"        About   : {xml.description}")
                lines.append(f"        Apply   : {xml.apply_hint}")
        else:
            lines.append("    XML configs : none")

        lines.append("")

    return "\n".join(lines) + "\n"
