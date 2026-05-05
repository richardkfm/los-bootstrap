"""Logo / banner sanity tests."""

from __future__ import annotations

from los_bootstrap import __version__
from los_bootstrap.logo import LOGO, banner


def test_full_banner_contains_logo_and_version():
    out = banner()
    assert "LOS" not in out  # ASCII spelled out in shadow font, not literal "LOS"
    assert "BOOTSTRAP" not in out  # same — drawn glyphs, not the literal word
    assert __version__ in out
    # Sanity: the block-shadow row for the L is present.
    assert "███████╗" in out


def test_compact_banner_is_short_and_versioned():
    out = banner(compact=True)
    assert "los · bootstrap" in out
    assert __version__ in out
    assert out.count("\n") == 1


def test_logo_is_multiline_block():
    assert LOGO.count("\n") >= 6
