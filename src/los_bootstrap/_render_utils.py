"""Shared rendering helpers used across audit/location/harden reports.

Each report module renders its findings in three buckets — actionable,
passing, info — with prose wrapped at 72 columns. The helpers here factor
out the parts that were duplicated verbatim across `report.py`,
`location/report.py`, and `harden/report.py`.
"""

from __future__ import annotations

import textwrap
from typing import Callable, Hashable, Iterable, TypeVar

T = TypeVar("T")
S = TypeVar("S", bound=Hashable)


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
