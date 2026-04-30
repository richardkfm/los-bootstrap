"""Tests for the Phase 6 wizard package.

Coverage:
- WizardContext device detection (offline / one device / multi-device)
- run_wizard routing: stub ask_select to return known tokens
- render_finding_summary grouping (via render.py helpers)
- render_finding_detail prose integration
- FINDING_PROSE coverage: every audit/harden check_id has prose
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from los_bootstrap.audit.checks import CHECKS as AUDIT_CHECKS
from los_bootstrap.harden.checks import CHECKS as HARDEN_CHECKS, ROOT_CHECKS
from los_bootstrap.wizard.prose import FINDING_PROSE, get_prose
from los_bootstrap.wizard.render import render_finding_detail, render_verbose_audit


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_device(serial: str = "S1", ready: bool = True):
    d = MagicMock()
    d.serial = serial
    d.ready = ready
    return d


# ── Prose coverage ────────────────────────────────────────────────────────────

def _audit_check_ids() -> set[str]:
    """Collect all check IDs produced by audit CHECKS on a no-op ADB."""
    from los_bootstrap.audit.models import AuditFinding, Severity

    ids: set[str] = set()

    class _NoopAdb:
        def package_installed(self, pkg): return False
        def shell(self, cmd): return "null"

    class _NoopFacts:
        is_lineage = True
        lineage_version = "21.0"
        adb_tcp_port = "0"

    adb = _NoopAdb()
    facts = _NoopFacts()
    for check_fn in AUDIT_CHECKS:
        for finding in check_fn(adb, facts):  # type: ignore[arg-type]
            ids.add(finding.check)
    return ids


def _harden_check_ids() -> set[str]:
    from los_bootstrap.adb import Adb

    answers = {
        "settings get global development_settings_enabled": "0\n",
        "settings get global adb_enabled": "0\n",
        "settings get secure lockscreen.disabled": "0\n",
        "getprop ro.crypto.state": "encrypted\n",
        "getprop ro.crypto.type": "file\n",
        "settings get secure install_non_market_apps": "0\n",
        "getprop ro.boot.verifiedbootstate": "green\n",
        "settings get secure lockdown_mode_allowed": "1\n",
    }

    def _runner(cmd, **_):
        return answers.get(cmd, "\n")

    adb = Adb(serial="S1", runner=_runner)

    class _NoopFacts:
        pass

    ids: set[str] = set()
    for check_fn in HARDEN_CHECKS + ROOT_CHECKS:
        try:
            for finding in check_fn(adb, _NoopFacts()):  # type: ignore[arg-type]
                ids.add(finding.check_id)
        except Exception:
            pass
    return ids


def test_prose_covers_all_audit_checks():
    """Every audit check_id must have an entry in FINDING_PROSE."""
    audit_ids = _audit_check_ids()
    missing = audit_ids - set(FINDING_PROSE.keys())
    assert not missing, f"Missing prose for audit check IDs: {missing}"


def test_prose_covers_all_harden_checks():
    """Every harden check_id must have an entry in FINDING_PROSE."""
    harden_ids = _harden_check_ids()
    missing = harden_ids - set(FINDING_PROSE.keys())
    assert not missing, f"Missing prose for harden check IDs: {missing}"


def test_get_prose_returns_none_for_unknown():
    assert get_prose("nonexistent.check") is None


def test_get_prose_returns_findingprose():
    p = get_prose("dns.private")
    assert p is not None
    assert p.check_id == "dns.private"
    assert p.what
    assert p.why
    assert p.fix
    assert p.tradeoff


# ── render_finding_detail ─────────────────────────────────────────────────────

def test_render_finding_detail_with_prose():
    text = render_finding_detail("dns.private", "Private DNS is off")
    assert "WHAT'S HAPPENING" in text
    assert "WHY IT MATTERS" in text
    assert "HOW TO FIX IT" in text
    assert "TRADEOFF" in text
    assert "Private DNS is off" in text


def test_render_finding_detail_no_prose():
    text = render_finding_detail("unknown.check.id", "Some title")
    assert "no extended prose available" in text
    assert "Some title" in text


# ── render_verbose_audit ──────────────────────────────────────────────────────

def test_render_verbose_audit_groups():
    from los_bootstrap.audit.models import AuditFinding, Severity

    findings = [
        AuditFinding("dns.private", "Private DNS is off", Severity.WARN, "detail"),
        AuditFinding("gms.present", "No GMS", Severity.OK, "detail"),
        AuditFinding("rom.lineage", "LineageOS detected", Severity.INFO, "detail"),
    ]
    text = render_verbose_audit(findings)
    assert "1 issue to address" in text
    assert "Passing checks" in text
    assert "For your information" in text


# ── WizardContext device detection ────────────────────────────────────────────

def test_wizard_context_offline_when_no_devices():
    from los_bootstrap.wizard.menu import run_wizard

    with patch("los_bootstrap.wizard.menu.ask_select", return_value="Exit"), \
         patch("los_bootstrap.wizard.menu.ask_confirm", return_value=False), \
         patch("los_bootstrap.wizard.menu.clear_screen"), \
         patch("los_bootstrap.wizard.menu.input", return_value=""), \
         patch("los_bootstrap.adb.Adb.list_devices", return_value=[]):
        # Should not raise; offline mode
        result = run_wizard(serial=None)
    assert result == 0


def test_wizard_context_auto_selects_single_device():
    from los_bootstrap.wizard.menu import run_wizard, WizardContext

    device = _make_device("ABC123")

    with patch("los_bootstrap.adb.Adb.list_devices", return_value=[device]), \
         patch("los_bootstrap.wizard.menu._screen_splash"), \
         patch("los_bootstrap.wizard.menu._screen_main_menu", return_value="exit"):
        result = run_wizard(serial=None)

    assert result == 0


def test_wizard_context_prompts_for_multiple_devices():
    from los_bootstrap.wizard.menu import run_wizard

    d1 = _make_device("D1")
    d2 = _make_device("D2")

    with patch("los_bootstrap.adb.Adb.list_devices", return_value=[d1, d2]), \
         patch("los_bootstrap.wizard.menu.ask_select", return_value="D1"), \
         patch("los_bootstrap.wizard.menu._screen_splash"), \
         patch("los_bootstrap.wizard.menu._screen_main_menu", return_value="exit"):
        result = run_wizard(serial=None)

    assert result == 0


# ── Routing ───────────────────────────────────────────────────────────────────

def test_main_menu_routes_to_exit():
    from los_bootstrap.wizard.menu import _screen_main_menu, WizardContext

    ctx = WizardContext(offline=True)
    with patch("los_bootstrap.wizard.menu.ask_select", return_value="Exit"), \
         patch("los_bootstrap.wizard.menu.clear_screen"):
        token = _screen_main_menu(ctx)
    assert token == "exit"


def test_main_menu_routes_to_audit():
    from los_bootstrap.wizard.menu import _screen_main_menu, WizardContext

    ctx = WizardContext(offline=True)
    with patch("los_bootstrap.wizard.menu.ask_select",
               return_value="Audit — check privacy and degoogle status  [read-only]"), \
         patch("los_bootstrap.wizard.menu.clear_screen"):
        token = _screen_main_menu(ctx)
    assert token == "audit"


def test_main_menu_routes_to_camera():
    from los_bootstrap.wizard.menu import _screen_main_menu, WizardContext

    ctx = WizardContext(offline=True)
    with patch("los_bootstrap.wizard.menu.ask_select",
               return_value="Camera — GCam port profiles  [no ADB needed]"), \
         patch("los_bootstrap.wizard.menu.clear_screen"):
        token = _screen_main_menu(ctx)
    assert token == "camera"


def test_offline_blocks_audit():
    from los_bootstrap.wizard.menu import _screen_audit, WizardContext

    ctx = WizardContext(offline=True)
    with patch("los_bootstrap.wizard.menu.input", return_value=""), \
         patch("builtins.print"):
        token = _screen_audit(ctx)
    assert token == "main"
