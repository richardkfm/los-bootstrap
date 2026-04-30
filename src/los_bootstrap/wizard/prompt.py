"""Interactivity adapter: questionary with a plain input() fallback.

All wizard screens import from here. Patching ask_select / ask_confirm in
tests avoids any TTY requirement.
"""

from __future__ import annotations

from typing import Optional

try:
    import questionary  # type: ignore[import]
    _HAS_QUESTIONARY = True
except ImportError:
    _HAS_QUESTIONARY = False


# ANSI helpers (no-op on non-ANSI terminals; terminals ignore unknown seqs)
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"
RESET = "\033[0m"


def _plain_select(prompt: str, choices: list[str]) -> Optional[str]:
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        print(f"  {i}. {choice}")
    while True:
        raw = input("  Choice [1]: ").strip()
        if raw == "":
            return choices[0]
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print(f"  Enter a number between 1 and {len(choices)}.")


def _plain_confirm(prompt: str, default: bool = False) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    raw = input(f"{prompt} {hint} ").strip().lower()
    if raw == "":
        return default
    return raw in ("y", "yes")


def _plain_text(prompt: str) -> str:
    return input(f"{prompt}: ").strip()


def ask_select(prompt: str, choices: list[str]) -> Optional[str]:
    """Present a menu; return the selected string, or None if aborted."""
    if _HAS_QUESTIONARY:
        return questionary.select(prompt, choices=choices).ask()
    return _plain_select(prompt, choices)


def ask_confirm(prompt: str, default: bool = False) -> bool:
    if _HAS_QUESTIONARY:
        result = questionary.confirm(prompt, default=default).ask()
        return bool(result)
    return _plain_confirm(prompt, default)


def ask_text(prompt: str) -> str:
    if _HAS_QUESTIONARY:
        result = questionary.text(prompt).ask()
        return result or ""
    return _plain_text(prompt)


def clear_screen() -> None:
    import os
    os.system("cls" if os.name == "nt" else "clear")
