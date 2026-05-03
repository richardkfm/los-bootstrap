"""Thin, testable wrapper around the `heimdall` CLI (Samsung devices).

Heimdall is an open-source alternative to Samsung's proprietary Odin tool.
It communicates with Samsung devices in Download Mode over USB.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


CommandRunner = Callable[[Sequence[str]], "HeimdallResult"]


class HeimdallNotFoundError(RuntimeError):
    """Raised when `heimdall` is not on PATH."""


class HeimdallCommandError(RuntimeError):
    """Raised when a heimdall invocation exits non-zero."""


@dataclass(frozen=True)
class HeimdallResult:
    returncode: int
    stdout: str
    stderr: str


def _default_runner(argv: Sequence[str]) -> HeimdallResult:
    if shutil.which(argv[0]) is None:
        raise HeimdallNotFoundError(f"`{argv[0]}` not found on PATH")
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    return HeimdallResult(proc.returncode, proc.stdout, proc.stderr)


def heimdall_available(binary: str = "heimdall") -> bool:
    """Return True if the `heimdall` binary is installed on the host."""
    return shutil.which(binary) is not None


class Heimdall:
    """Wrapper around `heimdall`. Inject `runner` in tests."""

    def __init__(
        self,
        runner: Optional[CommandRunner] = None,
        binary: str = "heimdall",
    ) -> None:
        self.binary = binary
        self._run = runner or _default_runner

    def detect(self) -> bool:
        """Return True if a Samsung device in Download Mode is reachable."""
        result = self._run([self.binary, "detect"])
        return result.returncode == 0

    def flash(self, partition: str, image_path: str) -> HeimdallResult:
        """Flash image to a named partition.

        Heimdall uses `--PARTITION_NAME` flag syntax; partition names are
        taken from the device's PIT (partition information table).
        Common values: RECOVERY, BOOT, SYSTEM.
        """
        result = self._run(
            [self.binary, "flash", f"--{partition.upper()}", image_path]
        )
        if result.returncode != 0:
            raise HeimdallCommandError(
                f"heimdall flash {partition} failed: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result

    def print_pit(self) -> str:
        """Dump the partition information table from the connected device."""
        result = self._run([self.binary, "print-pit"])
        return result.stdout + result.stderr
