"""Execute a FlashPlan against real devices (mutating; --confirm gated).

Only this module calls mutating fastboot/heimdall/adb methods. Every
destructive step requires confirm=True to run.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

from .fastboot import Fastboot, FastbootCommandError
from .heimdall import Heimdall, HeimdallCommandError, HeimdallNotFoundError
from .models import FlashPlan, FlashResult, FlashStep, FlashStepKind
from ..adb import Adb, AdbCommandError


def execute_flash_plan(
    plan: FlashPlan,
    adb: Adb,
    fastboot: Fastboot,
    heimdall: Optional[Heimdall] = None,
    confirm: bool = False,
    dry_run: bool = False,
    pause: Optional[Callable[[str], object]] = None,
) -> FlashResult:
    """Run every step in *plan*, honouring confirm/dry_run flags.

    Steps with is_destructive=True are skipped unless confirm=True.
    Steps with kind=MANUAL print their guidance and then block on `pause`
    (default: input) until the user has completed the action — the next
    step usually depends on it. Inject `pause` in tests.
    """
    result = FlashResult()
    if pause is None:
        pause = input

    for step in plan.steps:
        _print_step_header(step, dry_run)

        if step.kind == FlashStepKind.MANUAL:
            if step.guidance:
                sys.stdout.write(step.guidance + "\n")
            if not dry_run:
                try:
                    pause("  Press Enter once done (Ctrl-C to abort)... ")
                except (EOFError, KeyboardInterrupt):
                    result.errors.append(f"aborted at manual step: {step.description}")
                    sys.stderr.write("\n  Aborted.\n")
                    return result
            result.steps_skipped += 1
            continue

        if dry_run:
            result.steps_ok += 1
            continue

        if step.is_destructive and not confirm:
            print("  → skipped (pass --confirm to run destructive steps)")
            result.steps_skipped += 1
            continue

        try:
            _execute_step(step, adb, fastboot, heimdall)
            result.steps_ok += 1
        except (AdbCommandError, FastbootCommandError, HeimdallCommandError,
                HeimdallNotFoundError) as exc:
            result.errors.append(str(exc))
            sys.stderr.write(f"  ERROR: {exc}\n")

    return result


def _print_step_header(step: FlashStep, dry_run: bool) -> None:
    prefix = "DRY RUN" if dry_run else "RUN"
    if step.kind == FlashStepKind.MANUAL:
        prefix = "MANUAL"
    print(f"\n[{prefix}] {step.description}")
    if step.command:
        print(f"  $ {step.command}")


def _execute_step(
    step: FlashStep,
    adb: Adb,
    fastboot: Fastboot,
    heimdall: Optional[Heimdall],
) -> None:
    args = step.args
    kind = step.kind

    if kind == FlashStepKind.ADB_REBOOT:
        target = args[0] if args else None
        adb.reboot(target)

    elif kind == FlashStepKind.ADB_SIDELOAD:
        adb.sideload(args[0])

    elif kind == FlashStepKind.FASTBOOT_UNLOCK:
        fastboot.oem_unlock()

    elif kind == FlashStepKind.FASTBOOT_FLASH:
        fastboot.flash(args[0], args[1])

    elif kind == FlashStepKind.FASTBOOT_REBOOT:
        target = args[0] if args else None
        fastboot.reboot(target)

    elif kind == FlashStepKind.FASTBOOT_UPDATE:
        fastboot.update(args[0])

    elif kind == FlashStepKind.HEIMDALL_FLASH:
        if heimdall is None:
            raise HeimdallNotFoundError(
                "heimdall is required for this step but was not provided"
            )
        heimdall.flash(args[0], args[1])
