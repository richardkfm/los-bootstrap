"""Interactive wizard for los-bootstrap.

Public API: run_wizard(serial) -> int
Called by cli.main() when no subcommand is provided.
"""

from .menu import run_wizard

__all__ = ["run_wizard"]
