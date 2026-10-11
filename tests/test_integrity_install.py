"""Tests for `integrity install` (Phase 12 mutating path). ADB fully mocked.

Network is never touched: every test either uses a local zip or stops before
the fetch. A real zip with a module.prop is built on disk per test.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from los_bootstrap.adb import Adb, AdbResult
from los_bootstrap.integrity import load_module_sources
from los_bootstrap.integrity.install import (
    detect_root_method,
    read_module_prop,
    run_install,
    sha256_file,
)


def _make_module(path: Path, *, with_prop: bool = True, module_id: str = "playintegrityfix") -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        if with_prop:
            zf.writestr(
                "module.prop",
                f"id={module_id}\nname=Play Integrity Fix\nversion=v1.0\n"
                "versionCode=1000\nauthor=someone\n",
            )
        zf.writestr("customize.sh", "true\n")
    return path


def _adb(*, has_root: bool = True, log: list | None = None) -> Adb:
    """Fake adb. Records push/shell calls in `log` if given."""
    def run(argv):
        assert argv[0] == "adb"
        sub = argv[3] if argv[1:3] == ["-s", "S1"] else argv[1]
        if log is not None:
            log.append(argv)
        if sub == "push":
            return AdbResult(0, "1 file pushed\n", "")
        if sub == "shell":
            cmd = argv[-1]
            if "command -v magisk" in cmd:
                return AdbResult(0, "/system/bin/magisk\n" if has_root else "", "")
            if "command -v" in cmd:  # ksud / apd probes
                return AdbResult(0, "", "")
            if "--install-module" in cmd:
                return AdbResult(0, "- Installing module\n- Done\n", "")
            if cmd.startswith("rm -f"):
                return AdbResult(0, "", "")
            return AdbResult(0, "", "")
        raise AssertionError(f"unexpected adb sub-command: {argv}")

    return Adb(serial="S1", runner=run)


# ── module.prop parsing ───────────────────────────────────────────────────────

def test_read_module_prop_ok(tmp_path):
    z = _make_module(tmp_path / "m.zip")
    info = read_module_prop(z)
    assert info is not None
    assert info.module_id == "playintegrityfix"
    assert info.version == "v1.0"
    assert info.author == "someone"


def test_read_module_prop_absent(tmp_path):
    z = _make_module(tmp_path / "m.zip", with_prop=False)
    assert read_module_prop(z) is None


def test_read_module_prop_not_a_zip(tmp_path):
    p = tmp_path / "notzip.zip"
    p.write_text("i am not a zip")
    assert read_module_prop(p) is None


def test_sha256_matches_hashlib(tmp_path):
    import hashlib

    z = _make_module(tmp_path / "m.zip")
    assert sha256_file(z) == hashlib.sha256(z.read_bytes()).hexdigest()


# ── root detection ────────────────────────────────────────────────────────────

def test_detect_root_method_magisk():
    method = detect_root_method(_adb(has_root=True))
    assert method is not None and method[0] == "Magisk"


def test_detect_root_method_none():
    assert detect_root_method(_adb(has_root=False)) is None


# ── guardrails ────────────────────────────────────────────────────────────────

def test_refuses_without_root(tmp_path):
    z = _make_module(tmp_path / "m.zip")
    out = io.StringIO()
    outcome = run_install(_adb(), module_path=str(z), fetch_name=None, root=False, confirm=True, out=out)
    assert outcome.status == "refused"
    assert "--root" in out.getvalue()


def test_refuses_without_a_source(tmp_path):
    out = io.StringIO()
    outcome = run_install(_adb(), module_path=None, fetch_name=None, root=True, confirm=True, out=out)
    assert outcome.status == "refused"


def test_refuses_both_sources(tmp_path):
    z = _make_module(tmp_path / "m.zip")
    out = io.StringIO()
    outcome = run_install(_adb(), module_path=str(z), fetch_name="x", root=True, confirm=True, out=out)
    assert outcome.status == "refused"


def test_refuses_zip_without_module_prop(tmp_path):
    z = _make_module(tmp_path / "m.zip", with_prop=False)
    out = io.StringIO()
    outcome = run_install(_adb(), module_path=str(z), fetch_name=None, root=True, confirm=True, out=out)
    assert outcome.status == "refused"
    assert "module.prop" in out.getvalue()


def test_refuses_missing_file(tmp_path):
    out = io.StringIO()
    outcome = run_install(
        _adb(), module_path=str(tmp_path / "nope.zip"), fetch_name=None, root=True, confirm=True, out=out
    )
    assert outcome.status == "refused"


def test_unknown_fetch_name_refused():
    out = io.StringIO()
    outcome = run_install(_adb(), module_path=None, fetch_name="does-not-exist", root=True, confirm=True, out=out)
    assert outcome.status == "refused"


# ── preview vs install ────────────────────────────────────────────────────────

def test_preview_without_confirm_does_not_touch_device(tmp_path):
    z = _make_module(tmp_path / "m.zip")
    log: list = []
    out = io.StringIO()
    outcome = run_install(_adb(log=log), module_path=str(z), fetch_name=None, root=True, confirm=False, out=out)
    assert outcome.status == "previewed"
    text = out.getvalue()
    assert "sha256" in text
    # all three warnings present
    for word in ("Fragility", "Liability shift", "Root attack surface"):
        assert word in text
    # nothing was pushed or installed
    assert not any(a[3] == "push" or "--install-module" in a[-1] for a in log if len(a) > 3)


def test_confirm_installs_via_magisk(tmp_path):
    z = _make_module(tmp_path / "m.zip")
    log: list = []
    out = io.StringIO()
    outcome = run_install(_adb(log=log), module_path=str(z), fetch_name=None, root=True, confirm=True, out=out)
    assert outcome.status == "installed"
    assert any(a[3] == "push" for a in log)
    assert any("--install-module" in a[-1] for a in log)
    assert "Reboot" in out.getvalue()


def test_confirm_without_root_method_errors(tmp_path):
    z = _make_module(tmp_path / "m.zip")
    out = io.StringIO()
    outcome = run_install(
        _adb(has_root=False), module_path=str(z), fetch_name=None, root=True, confirm=True, out=out
    )
    assert outcome.status == "error"
    assert "rooted" in out.getvalue().lower()


# ── registry ──────────────────────────────────────────────────────────────────

def test_registry_loads_and_excludes_keyboxes():
    sources = load_module_sources()
    assert sources
    names = {s.name for s in sources}
    assert "playintegrityfork" in names
    # keyboxes are a non-goal: no listed module may be a keybox/TrickyStore one.
    for s in sources:
        assert "trickystore" not in s.repo.lower()
        assert "keybox" not in s.repo.lower()
