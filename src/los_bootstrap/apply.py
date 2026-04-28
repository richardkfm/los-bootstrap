"""Execute a `Plan`.

The applier only ever runs after the user passes `--confirm`. Each
executable step is written to stdout before it runs so the user has a
last chance to spot something they did not expect.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, TextIO

from .adb import Adb, AdbCommandError
from .plan import Plan, PlanStep, StepKind


@dataclass
class StepResult:
    step: PlanStep
    status: str  # "ok" | "skipped" | "manual" | "missing_apk" | "error"
    detail: str = ""


@dataclass
class ApplyResult:
    profile_name: str
    results: list[StepResult] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results:
            out[r.status] = out.get(r.status, 0) + 1
        return out

    def had_errors(self) -> bool:
        return any(r.status == "error" for r in self.results)


def _extract_apk_path(command: str) -> Optional[Path]:
    # `adb install -r /abs/path/to.apk` — pull out the last token.
    m = re.match(r"^adb install(?:\s+-r)?\s+(.+)$", command)
    if not m:
        return None
    return Path(m.group(1))


def _extract_setting(command: str) -> Optional[tuple[str, str, str]]:
    m = re.match(
        r"^adb shell settings put (\w+) (\S+) (.+)$",
        command,
    )
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def apply_plan(
    adb: Adb,
    plan: Plan,
    *,
    dry_run: bool = False,
    out: TextIO = sys.stdout,
) -> ApplyResult:
    """Run the executable steps in `plan` against `adb`.

    The caller is responsible for gating on `--confirm`. `dry_run`
    prints the commands without running them.
    """
    result = ApplyResult(profile_name=plan.profile_name)

    out.write(f"Applying profile: {plan.profile_name}\n")
    if dry_run:
        out.write("(dry run — no commands will be executed)\n")
    out.write("\n")

    for i, step in enumerate(plan.steps, 1):
        prefix = f"[{i:2d}/{len(plan.steps)}]"

        if step.kind == StepKind.SKIP:
            out.write(f"{prefix} skip   : {step.summary}\n")
            result.results.append(
                StepResult(step=step, status="skipped", detail=step.skipped_reason or "")
            )
            continue

        if step.kind == StepKind.MANUAL_INSTALL:
            out.write(f"{prefix} manual : {step.summary}\n")
            result.results.append(
                StepResult(step=step, status="manual", detail="user must install via store")
            )
            continue

        if step.kind == StepKind.INSTALL_APK:
            if step.missing_apk_path is not None or step.command is None:
                out.write(
                    f"{prefix} skip   : {step.summary} "
                    f"(missing APK: {step.missing_apk_path})\n"
                )
                result.results.append(
                    StepResult(
                        step=step,
                        status="missing_apk",
                        detail=step.missing_apk_path or "no command",
                    )
                )
                continue
            apk_path = _extract_apk_path(step.command)
            out.write(f"{prefix} run    : {step.command}\n")
            if dry_run or apk_path is None:
                result.results.append(
                    StepResult(step=step, status="ok", detail="dry-run")
                )
                continue
            try:
                stdout = adb.install_apk(str(apk_path))
                result.results.append(
                    StepResult(step=step, status="ok", detail=stdout.strip())
                )
            except AdbCommandError as exc:
                out.write(f"        error  : {exc}\n")
                result.results.append(
                    StepResult(step=step, status="error", detail=str(exc))
                )
            continue

        if step.kind == StepKind.SET_SETTING:
            if step.command is None:
                continue
            parsed = _extract_setting(step.command)
            out.write(f"{prefix} run    : {step.command}\n")
            if dry_run or parsed is None:
                result.results.append(
                    StepResult(step=step, status="ok", detail="dry-run")
                )
                continue
            namespace, key, value = parsed
            try:
                adb.setting_put(namespace, key, value)
                result.results.append(StepResult(step=step, status="ok"))
            except AdbCommandError as exc:
                out.write(f"        error  : {exc}\n")
                result.results.append(
                    StepResult(step=step, status="error", detail=str(exc))
                )
            continue

    counts = result.counts()
    out.write("\n")
    out.write(
        "Done: "
        + ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        + ".\n"
    )
    return result
