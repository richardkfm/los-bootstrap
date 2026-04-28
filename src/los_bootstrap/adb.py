"""Thin, testable wrapper around the `adb` binary.

All ADB IO funnels through `Adb`. Tests inject a fake `runner` so no real
`adb` is required. Read-only methods are always available. Mutating
methods (`install_apk`, `setting_put`) are used by the Phase 2 applier
and only ever run after the user passes `--confirm`.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional, Sequence


CommandRunner = Callable[[Sequence[str]], "AdbResult"]


class AdbNotFoundError(RuntimeError):
    """Raised when the `adb` binary cannot be located on PATH."""


class AdbCommandError(RuntimeError):
    """Raised when an `adb` invocation exits non-zero."""


@dataclass(frozen=True)
class AdbResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str  # "device", "unauthorized", "offline", ...

    @property
    def ready(self) -> bool:
        return self.state == "device"


def _default_runner(argv: Sequence[str]) -> AdbResult:
    if shutil.which(argv[0]) is None:
        raise AdbNotFoundError(f"`{argv[0]}` not found on PATH")
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    return AdbResult(proc.returncode, proc.stdout, proc.stderr)


class Adb:
    """Wrapper around `adb`. Inject `runner` in tests."""

    def __init__(
        self,
        serial: Optional[str] = None,
        runner: Optional[CommandRunner] = None,
        binary: str = "adb",
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

    def raw(self, *args: str) -> AdbResult:
        return self._run(self._argv(*args))

    def shell(self, command: str) -> str:
        result = self.raw("shell", command)
        if result.returncode != 0:
            raise AdbCommandError(
                f"adb shell `{command}` failed: {result.stderr.strip()}"
            )
        return result.stdout

    def list_devices(self) -> list[AdbDevice]:
        result = self.raw("devices")
        if result.returncode != 0:
            raise AdbCommandError(f"adb devices failed: {result.stderr.strip()}")
        return parse_devices(result.stdout)

    def getprop(self, key: str) -> str:
        return self.shell(f"getprop {key}").strip()

    def package_installed(self, package: str) -> bool:
        # `pm list packages <pkg>` returns lines of form `package:<name>`.
        out = self.shell(f"pm list packages {package}")
        for line in out.splitlines():
            if line.strip() == f"package:{package}":
                return True
        return False

    def setting_get(self, namespace: str, key: str) -> str:
        """Return the current value of `settings get <namespace> <key>`.

        The `settings` CLI prints `null` when a key is unset; we
        normalize that to an empty string for easier comparison.
        """
        out = self.shell(f"settings get {namespace} {key}").strip()
        return "" if out == "null" else out

    def install_apk(self, apk_path: str, replace: bool = True) -> str:
        """Install an APK from a local path. Mutating; applier-only."""
        args = ["install"]
        if replace:
            args.append("-r")
        args.append(apk_path)
        result = self.raw(*args)
        if result.returncode != 0:
            raise AdbCommandError(
                f"adb install {apk_path} failed: "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result.stdout

    def setting_put(self, namespace: str, key: str, value: str) -> None:
        """Run `settings put <namespace> <key> <value>`. Mutating."""
        self.shell(
            f"settings put {namespace} {key} {shlex.quote(value)}"
        )


def parse_devices(stdout: str) -> list[AdbDevice]:
    """Parse the output of `adb devices`."""
    devices: list[AdbDevice] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append(AdbDevice(serial=parts[0], state=parts[1]))
    return devices
