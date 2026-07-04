"""Tests for the shared color/wrap helpers."""

from __future__ import annotations

from los_bootstrap._render_utils import color_enabled, paint, paint_glyph


def test_no_color_env_disables(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    assert color_enabled() is False


def test_force_color_env_enables(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert color_enabled() is True


def test_paint_disabled_returns_plain():
    assert paint("hello", "red", enabled=False) == "hello"


def test_paint_enabled_wraps_ansi():
    out = paint("hello", "red", enabled=True)
    assert out.startswith("\033[31m") and out.endswith("\033[0m")
    assert "hello" in out


def test_paint_unknown_color_is_noop():
    assert paint("x", "mauve", enabled=True) == "x"


def test_paint_glyph_colors_by_severity():
    assert "\033[32m" in paint_glyph("✓", enabled=True)   # green
    assert "\033[31m" in paint_glyph("✗", enabled=True)   # red
    assert paint_glyph("Z", enabled=True) == "Z"          # unmapped


def test_reports_are_plain_when_disabled(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    from los_bootstrap.harden.models import HardenFinding, HardenReport, HardenStatus
    from los_bootstrap.harden.report import render_harden_report

    report = HardenReport(findings=(
        HardenFinding(
            check_id="x", title="t", status=HardenStatus.FAIL,
            detail="d", why="w", tradeoff="tr", fix_hint="f",
        ),
    ))
    assert "\033[" not in render_harden_report(report)
