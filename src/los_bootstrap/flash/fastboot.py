"""Thin, testable wrapper around the `fastboot` binary.

Mirrors the design of adb.py: inject a `runner` in tests so no real device
is needed. Mutating methods are used only by flash.py and only after --confirm.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


CommandRunner = Callable[[Sequence[str]], "FastbootResult"]


class FastbootNotFoundError(RuntimeError):
    """Raised when the `fastboot` binary cannot be located on PATH."""


class FastbootCommandError(RuntimeError):
    """Raised when a fastboot invocation exits non-zero."""


@dataclass(frozen=True)
class FastbootResult:
    returncode: int
    stdout: str
    stderr: str


def _default_runner(argv: Sequence[str]) -> FastbootResult:
    if shutil.which(argv[0]) is None:
        raise FastbootNotFoundError(f"`{argv[0]}` not found on PATH")
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    return FastbootResult(proc.returncode, proc.stdout, proc.stderr)


class Fastboot:
    """Wrapper around `fastboot`. Inject `runner` in tests."""

    def __init__(
        self,
        serial: Optional[str] = None,
        runner: Optional[CommandRunner] = None,
        binary: str = "fastboot",
    ) -> None:
        self.serial = serial
        self.binary = binary
        self._run = runner or _default_runner

    def _argv(self, *args: str) -> list[str]:
        argv = [self.binary]
        if self.serial:
            argv += ["-s", self.serial]
        argv += list(args)
        return argv

    def raw(self, *args: str) -> FastbootResult:
        return self._run(self._argv(*args))

    def devices(self) -> list[str]:
        """Return serials of devices currently in fastboot mode."""
        result = self._run([self.binary, "devices"])
        serials: list[str] = []
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "fastboot":
                serials.append(parts[0])
        return serials

    def getvar(self, key: str) -> str:
        """Query a fastboot variable. fastboot writes results to stderr."""
        result = self.raw("getvar", key)
        needle = key.lower() + ":"
        for line in (result.stderr + result.stdout).splitlines():
            if line.lower().startswith(needle):
                return line.split(":", 1)[1].strip()
        return ""

    def flash(self, partition: str, image_path: str) -> FastbootResult:
        """Flash image to partition. Mutating; flash.py-only."""
        result = self.raw("flash", partition, image_path)
        if result.returncode != 0:
            raise FastbootCommandError(
                f"fastboot flash {partition} failed: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result

    def reboot(self, target: Optional[str] = None) -> FastbootResult:
        """Reboot device, optionally to 'recovery' or 'bootloader'. Mutating."""
        args: tuple[str, ...] = ("reboot", target) if target else ("reboot",)
        return self.raw(*args)

    def oem_unlock(self) -> FastbootResult:
        """Run `fastboot flashing unlock`. Destructive — wipes all data."""
        return self.raw("flashing", "unlock")

    def update(self, zip_path: str) -> FastbootResult:
        """Run `fastboot update <zip>` for A/B devices. Mutating."""
        result = self.raw("update", zip_path)
        if result.returncode != 0:
            raise FastbootCommandError(
                f"fastboot update failed: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result
