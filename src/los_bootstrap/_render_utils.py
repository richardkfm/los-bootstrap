"""Shared rendering helpers used across audit/location/harden reports.

Each report module renders its findings in three buckets — actionable,
passing, info — with prose wrapped at 72 columns. The helpers here factor
out the parts that were duplicated verbatim across `report.py`,
`location/report.py`, and `harden/report.py`.
"""

from __future__ import annotations

import os
import sys
import textwrap
from typing import Callable, Hashable, Iterable, Optional, TextIO, TypeVar

T = TypeVar("T")
S = TypeVar("S", bound=Hashable)

_ANSI = {
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "cyan": "\033[36m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}
_RESET = "\033[0m"

# Which color a report glyph gets when color is enabled.
GLYPH_COLORS = {
    "✓": "green",
    "!": "yellow",
    "✗": "red",
    "·": "dim",
    "?": "dim",
}


def color_enabled(stream: Optional[TextIO] = None) -> bool:
    """True when ANSI color should be emitted (TTY, honoring NO_COLOR/FORCE_COLOR)."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if stream is None:
        stream = sys.stdout
    return hasattr(stream, "isatty") and stream.isatty()


def paint(text: str, color: str, enabled: Optional[bool] = None) -> str:
    """Wrap `text` in an ANSI color when enabled; plain text otherwise."""
    if enabled is None:
        enabled = color_enabled()
    code = _ANSI.get(color)
    if not enabled or code is None:
        return text
    return f"{code}{text}{_RESET}"


def paint_glyph(glyph: str, enabled: Optional[bool] = None) -> str:
    """Color a status glyph (✓ ! ✗ · ?) by its conventional severity color."""
    color = GLYPH_COLORS.get(glyph)
    return paint(glyph, color, enabled) if color else glyph


def wrap(text: str, indent: str, width: int = 72) -> str:
    """Word-wrap text with the given indent on every line."""
    return textwrap.fill(
        text, width=width, initial_indent=indent, subsequent_indent=indent
    )


def partition_findings(
    findings: Iterable[T],
    classify: Callable[[T], S],
    actionable: Iterable[S],
    passing: Iterable[S],
    info: Iterable[S],
) -> tuple[list[T], list[T], list[T]]:
    """Bucket findings into (actionable, passing, info) by their status.

    `classify` returns the status value for a given finding (e.g.
    `lambda f: f.severity`). Each bucket parameter is the set of status
    values that belong in that bucket.
    """
    actionable_set = set(actionable)
    passing_set = set(passing)
    info_set = set(info)
    a: list[T] = []
    p: list[T] = []
    i: list[T] = []
    for f in findings:
        s = classify(f)
        if s in actionable_set:
            a.append(f)
        elif s in passing_set:
            p.append(f)
        elif s in info_set:
            i.append(f)
    return a, p, i
