"""Loader for the declared spoofing-module registry (`integrity_data/modules.yml`).

The registry only names upstream repos; it never contains module binaries or
keyboxes. `integrity install --fetch <name>` resolves a name to a repo and
pulls its latest release asset at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Optional

import yaml


@dataclass(frozen=True)
class ModuleSource:
    name: str
    repo: str
    asset_suffix: str
    summary: str


def _load_raw() -> list[dict]:
    text = resources.files("los_bootstrap").joinpath("integrity_data/modules.yml").read_text(
        encoding="utf-8"
    )
    data = yaml.safe_load(text) or {}
    modules = data.get("modules", [])
    return modules if isinstance(modules, list) else []


def load_module_sources() -> tuple[ModuleSource, ...]:
    sources: list[ModuleSource] = []
    for entry in _load_raw():
        if not isinstance(entry, dict) or "name" not in entry or "repo" not in entry:
            continue
        sources.append(
            ModuleSource(
                name=str(entry["name"]),
                repo=str(entry["repo"]),
                asset_suffix=str(entry.get("asset_suffix", ".zip")),
                summary=" ".join(str(entry.get("summary", "")).split()),
            )
        )
    return tuple(sources)


def find_module_source(name: str) -> Optional[ModuleSource]:
    for source in load_module_sources():
        if source.name == name:
            return source
    return None
