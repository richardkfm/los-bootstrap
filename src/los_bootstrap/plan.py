"""Turn a parsed profile into a reviewable, executable plan.

A `Plan` is a list of `PlanStep`s. The user runs `los-bootstrap plan`
to inspect it and `los-bootstrap apply --confirm` to execute it. The
planner is read-only: it only inspects device state to decide whether
each step is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .adb import Adb
from .profiles import AppEntry, Profile, SettingEntry


class StepKind(str, Enum):
    INSTALL_APK = "install_apk"      # `adb install <path>` — executable
    MANUAL_INSTALL = "manual_install"  # install via F-Droid / Aurora — informational
    SET_SETTING = "set_setting"      # `adb shell settings put ...` — executable
    SKIP = "skip"                    # already satisfied


@dataclass(frozen=True)
class PlanStep:
    kind: StepKind
    summary: str          # one-line human description
    target: str           # package id, or "namespace.key"
    rationale: str = ""   # why this step exists (from profile note)
    # For executable steps: the literal command we will run, exposed so
    # the user can audit it before approving. `None` for manual / skip.
    command: Optional[str] = None
    # Filled when kind == SKIP, to explain why we are skipping.
    skipped_reason: Optional[str] = None
    # Filled when kind == INSTALL_APK and we cannot find the staged APK.
    missing_apk_path: Optional[str] = None
    # Filled when the APK will be fetched at apply time.
    # "fdroid://<package>" → resolved via F-Droid API; plain HTTPS → direct download.
    download_url: Optional[str] = None


@dataclass(frozen=True)
class Plan:
    profile_name: str
    description: str
    steps: tuple[PlanStep, ...] = field(default_factory=tuple)

    def executable_steps(self) -> tuple[PlanStep, ...]:
        return tuple(
            s for s in self.steps
            if s.kind in (StepKind.INSTALL_APK, StepKind.SET_SETTING)
        )

    def manual_steps(self) -> tuple[PlanStep, ...]:
        return tuple(s for s in self.steps if s.kind == StepKind.MANUAL_INSTALL)

    def skipped_steps(self) -> tuple[PlanStep, ...]:
        return tuple(s for s in self.steps if s.kind == StepKind.SKIP)


def _resolve_apk(app: AppEntry, apk_dir: Optional[Path]) -> tuple[Optional[Path], Optional[str]]:
    """Return (resolved_path, error_string)."""
    if not app.apk:
        return None, "no apk filename declared"
    if apk_dir is None:
        return None, "no --apk-dir provided"
    candidate = apk_dir / app.apk
    if not candidate.is_file():
        return None, f"file not found at {candidate}"
    return candidate, None


def _plan_app(adb: Adb, app: AppEntry, apk_dir: Optional[Path], fetch: bool) -> PlanStep:
    if adb.package_installed(app.id):
        return PlanStep(
            kind=StepKind.SKIP,
            summary=f"{app.id} already installed",
            target=app.id,
            rationale=app.note,
            skipped_reason="package already present on device",
        )
    if app.source == "sideload":
        path, err = _resolve_apk(app, apk_dir)
        if path is None:
            if fetch and app.url:
                return PlanStep(
                    kind=StepKind.INSTALL_APK,
                    summary=f"download + install {app.id}",
                    target=app.id,
                    rationale=app.note,
                    download_url=app.url,
                )
            return PlanStep(
                kind=StepKind.INSTALL_APK,
                summary=f"sideload {app.id}",
                target=app.id,
                rationale=app.note,
                command=None,
                missing_apk_path=err,
            )
        return PlanStep(
            kind=StepKind.INSTALL_APK,
            summary=f"sideload {app.id} from {path.name}",
            target=app.id,
            rationale=app.note,
            command=f"adb install -r {path}",
        )
    if app.source == "fdroid":
        if fetch:
            return PlanStep(
                kind=StepKind.INSTALL_APK,
                summary=f"download + install {app.id} from F-Droid",
                target=app.id,
                rationale=app.note or "F-Droid keeps this app updated.",
                download_url=f"fdroid://{app.id}",
            )
        return PlanStep(
            kind=StepKind.MANUAL_INSTALL,
            summary=f"install {app.id} via F-Droid",
            target=app.id,
            rationale=app.note or "F-Droid keeps this app updated.",
        )
    # Aurora Store: always manual — cannot download Play Store apps automatically.
    return PlanStep(
        kind=StepKind.MANUAL_INSTALL,
        summary=f"install {app.id} via Aurora Store",
        target=app.id,
        rationale=app.note or "Aurora Store keeps this app updated.",
    )


def _plan_setting(adb: Adb, entry: SettingEntry) -> PlanStep:
    target = f"{entry.namespace}.{entry.key}"
    try:
        current = adb.setting_get(entry.namespace, entry.key)
    except Exception:
        current = ""
    if current == entry.value:
        return PlanStep(
            kind=StepKind.SKIP,
            summary=f"{target} already set to {entry.value!r}",
            target=target,
            rationale=entry.note,
            skipped_reason="setting already has the desired value",
        )
    return PlanStep(
        kind=StepKind.SET_SETTING,
        summary=(
            f"set {target} = {entry.value!r}"
            + (f" (was {current!r})" if current else "")
        ),
        target=target,
        rationale=entry.note,
        command=f"adb shell settings put {entry.namespace} {entry.key} {entry.value}",
    )


def build_plan(
    adb: Adb,
    profile: Profile,
    apk_dir: Optional[Path] = None,
    fetch: bool = True,
) -> Plan:
    steps: list[PlanStep] = []
    for app in profile.apps:
        steps.append(_plan_app(adb, app, apk_dir, fetch))
    for setting in profile.settings:
        steps.append(_plan_setting(adb, setting))
    return Plan(
        profile_name=profile.name,
        description=profile.description,
        steps=tuple(steps),
    )


def render_plan(plan: Plan) -> str:
    """Pretty-print a plan for `los-bootstrap plan`."""
    lines: list[str] = []
    lines.append(f"Profile: {plan.profile_name}")
    if plan.description:
        for chunk in plan.description.splitlines():
            lines.append(f"  {chunk}")
    lines.append("")
    if not plan.steps:
        lines.append("  (this profile is empty)")
        return "\n".join(lines) + "\n"

    lines.append("Steps")
    lines.append("-----")
    for i, step in enumerate(plan.steps, 1):
        if step.download_url:
            glyph = "↓"  # ↓
        else:
            glyph = {
                StepKind.INSTALL_APK: "+",
                StepKind.MANUAL_INSTALL: "?",
                StepKind.SET_SETTING: "~",
                StepKind.SKIP: "=",
            }[step.kind]
        lines.append(f"  {i:2d} [{glyph}] {step.kind.value:14s} {step.summary}")
        if step.rationale:
            lines.append(f"        why    : {step.rationale}")
        if step.download_url:
            if step.download_url.startswith("fdroid://"):
                lines.append(f"        from   : F-Droid repo ({step.download_url[9:]})")
            else:
                lines.append(f"        from   : {step.download_url}")
        if step.command:
            lines.append(f"        run    : {step.command}")
        if step.missing_apk_path:
            lines.append(f"        note   : MISSING APK ({step.missing_apk_path})")
        if step.skipped_reason:
            lines.append(f"        note   : {step.skipped_reason}")

    n_exec = len(plan.executable_steps())
    n_manual = len(plan.manual_steps())
    n_skip = len(plan.skipped_steps())
    lines.append("")
    lines.append(
        f"Summary: {n_exec} to run, {n_manual} manual, {n_skip} already satisfied."
    )
    return "\n".join(lines) + "\n"
