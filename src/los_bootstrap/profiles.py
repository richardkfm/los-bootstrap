"""YAML profile loader.

Phase 1: parse-only. Profiles are read so we can validate the schema and
print them, but we never act on them yet. The applier lands in Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ProfileError(ValueError):
    """Raised when a profile YAML is malformed."""


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    apps: tuple[str, ...] = field(default_factory=tuple)  # app IDs to install
    settings: tuple[tuple[str, str, str], ...] = field(default_factory=tuple)
    # settings entries: (namespace, key, value), e.g. ("global", "private_dns_mode", "hostname")
    source: Path | None = None


def load_profile(path: Path) -> Profile:
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ProfileError(f"{path}: top-level must be a mapping")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise ProfileError(f"{path}: missing required string field 'name'")
    description = raw.get("description", "")
    if not isinstance(description, str):
        raise ProfileError(f"{path}: 'description' must be a string")
    apps_raw = raw.get("apps", [])
    if not isinstance(apps_raw, list) or not all(isinstance(a, str) for a in apps_raw):
        raise ProfileError(f"{path}: 'apps' must be a list of strings")
    settings_raw = raw.get("settings", [])
    settings: list[tuple[str, str, str]] = []
    if settings_raw:
        if not isinstance(settings_raw, list):
            raise ProfileError(f"{path}: 'settings' must be a list")
        for entry in settings_raw:
            if (
                not isinstance(entry, dict)
                or not {"namespace", "key", "value"} <= entry.keys()
            ):
                raise ProfileError(
                    f"{path}: each settings entry needs namespace/key/value"
                )
            settings.append((str(entry["namespace"]), str(entry["key"]), str(entry["value"])))
    return Profile(
        name=name,
        description=description,
        apps=tuple(apps_raw),
        settings=tuple(settings),
        source=path,
    )


def list_profiles(directory: Path) -> list[Profile]:
    if not directory.is_dir():
        return []
    return [load_profile(p) for p in sorted(directory.glob("*.yml"))]
