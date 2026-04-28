"""YAML profile loader.

Phase 2: profiles describe a reviewable plan — apps to install and
device settings to suggest. They are still inert until the planner
(`plan.py`) and applier (`apply.py`) act on them. The schema here is
the contract the rest of the tool depends on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Iterable

import yaml


class ProfileError(ValueError):
    """Raised when a profile YAML is malformed."""


# Sources we support for app entries. `fdroid` and `aurora` mean the
# user installs them through that store after the store is set up; the
# applier surfaces them as MANUAL steps. `sideload` means we will run
# `adb install <path>` against a local APK staged by the user.
APP_SOURCES = ("fdroid", "aurora", "sideload")

# Namespaces accepted by `settings put`. We refuse anything outside
# this list to keep accidents off the device.
SETTING_NAMESPACES = ("global", "secure", "system")


@dataclass(frozen=True)
class AppEntry:
    id: str  # Android package id, e.g. "org.fdroid.fdroid"
    source: str = "fdroid"  # one of APP_SOURCES
    apk: str | None = None  # filename for source=sideload
    url: str | None = None  # informational URL for the user
    note: str = ""


@dataclass(frozen=True)
class SettingEntry:
    namespace: str  # global | secure | system
    key: str
    value: str
    note: str = ""


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    apps: tuple[AppEntry, ...] = field(default_factory=tuple)
    settings: tuple[SettingEntry, ...] = field(default_factory=tuple)
    source: Path | None = None


def _coerce_app(raw: Any, where: str) -> AppEntry:
    if isinstance(raw, str):
        return AppEntry(id=raw)
    if not isinstance(raw, dict):
        raise ProfileError(f"{where}: each app must be a string or mapping")
    pkg = raw.get("id") or raw.get("package")
    if not isinstance(pkg, str) or not pkg:
        raise ProfileError(f"{where}: app entry missing 'id'")
    source = str(raw.get("source", "fdroid"))
    if source not in APP_SOURCES:
        raise ProfileError(
            f"{where}: app {pkg!r} has unknown source {source!r}; "
            f"expected one of {APP_SOURCES}"
        )
    apk = raw.get("apk")
    if apk is not None and not isinstance(apk, str):
        raise ProfileError(f"{where}: app {pkg!r}: 'apk' must be a string filename")
    if source == "sideload" and not apk:
        raise ProfileError(
            f"{where}: app {pkg!r} has source=sideload but no 'apk' filename"
        )
    url = raw.get("url")
    if url is not None and not isinstance(url, str):
        raise ProfileError(f"{where}: app {pkg!r}: 'url' must be a string")
    note = raw.get("note", "")
    if not isinstance(note, str):
        raise ProfileError(f"{where}: app {pkg!r}: 'note' must be a string")
    return AppEntry(id=pkg, source=source, apk=apk, url=url, note=note)


def _coerce_setting(raw: Any, where: str) -> SettingEntry:
    if not isinstance(raw, dict):
        raise ProfileError(f"{where}: each settings entry must be a mapping")
    missing = {"namespace", "key", "value"} - raw.keys()
    if missing:
        raise ProfileError(
            f"{where}: settings entry missing fields: {sorted(missing)}"
        )
    namespace = str(raw["namespace"])
    if namespace not in SETTING_NAMESPACES:
        raise ProfileError(
            f"{where}: settings namespace {namespace!r} not in {SETTING_NAMESPACES}"
        )
    key = str(raw["key"])
    if not key:
        raise ProfileError(f"{where}: settings 'key' must be non-empty")
    value = raw["value"]
    if not isinstance(value, (str, int, float, bool)):
        raise ProfileError(
            f"{where}: settings value must be a scalar (got {type(value).__name__})"
        )
    note = raw.get("note", "")
    if not isinstance(note, str):
        raise ProfileError(f"{where}: settings 'note' must be a string")
    return SettingEntry(namespace=namespace, key=key, value=str(value), note=note)


def load_profile(path: Path) -> Profile:
    """Parse a profile YAML file. Raises ProfileError on malformed input."""
    raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ProfileError(f"{path}: top-level must be a mapping")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise ProfileError(f"{path}: missing required string field 'name'")
    description = raw.get("description", "")
    if not isinstance(description, str):
        raise ProfileError(f"{path}: 'description' must be a string")

    apps_raw = raw.get("apps", []) or []
    if not isinstance(apps_raw, list):
        raise ProfileError(f"{path}: 'apps' must be a list")
    apps = tuple(_coerce_app(a, str(path)) for a in apps_raw)

    settings_raw = raw.get("settings", []) or []
    if not isinstance(settings_raw, list):
        raise ProfileError(f"{path}: 'settings' must be a list")
    settings = tuple(_coerce_setting(s, str(path)) for s in settings_raw)

    return Profile(
        name=name,
        description=description.strip(),
        apps=apps,
        settings=settings,
        source=path,
    )


def list_profiles(directory: Path) -> list[Profile]:
    if not directory.is_dir():
        return []
    return [load_profile(p) for p in sorted(directory.glob("*.yml"))]


def bundled_profiles_dir() -> Path:
    """Directory of profiles shipped with the package."""
    # `as_file` would be needed for zipped installs; for our editable /
    # wheel installs the package is on disk, so `files(...)` resolves
    # to a real path.
    return Path(str(resources.files("los_bootstrap").joinpath("profiles_data")))


def list_bundled_profiles() -> list[Profile]:
    return list_profiles(bundled_profiles_dir())


def find_profile(
    name_or_path: str,
    extra_dirs: Iterable[Path] = (),
) -> Profile:
    """Resolve a profile by name or path.

    Lookup order:
      1. literal file path (if it exists)
      2. each directory in `extra_dirs`, looking for `<name>.yml`
      3. bundled profiles in the package
    """
    p = Path(name_or_path)
    if p.is_file():
        return load_profile(p)
    candidates: list[Path] = []
    for d in extra_dirs:
        candidates.append(Path(d) / f"{name_or_path}.yml")
    candidates.append(bundled_profiles_dir() / f"{name_or_path}.yml")
    for cand in candidates:
        if cand.is_file():
            return load_profile(cand)
    raise ProfileError(
        f"profile {name_or_path!r} not found. Tried: "
        + ", ".join(str(c) for c in candidates)
    )
