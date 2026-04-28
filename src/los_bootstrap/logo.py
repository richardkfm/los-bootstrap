"""ASCII logo printed on CLI startup.

Kept in its own module so it can be reused in docs and tests, and so the
exact glyphs are easy to find when someone wants to tweak the brand.
"""

from . import __version__

# Two fonts deliberately combined:
#   - "LOS" in a chunky shadow-block style (visual anchor)
#   - "BOOTSTRAP" in a thin double-line capital style (technical feel)
# A vertical separator joins them, with a tagline column on the right.
LOGO = r"""
   ██╗      ██████╗ ███████╗  ╷  ╔╗ ╔═╗╔═╗╔╦╗╔═╗╔╦╗╦═╗╔═╗╔═╗
   ██║     ██╔═══██╗██╔════╝  │  ╠╩╗║ ║║ ║ ║ ╚═╗ ║ ╠╦╝╠═╣╠═╝
   ██║     ██║   ██║███████╗  │  ╚═╝╚═╝╚═╝ ╩ ╚═╝ ╩ ╩╚═╩ ╩╩
   ██║     ██║   ██║╚════██║  │   post-install · degoogled
   ███████╗╚██████╔╝███████║  │   adb-driven · audit-first
   ╚══════╝ ╚═════╝ ╚══════╝  ╵
"""

COMPACT = "« los · bootstrap »  post-install / degoogled / audit-first"


def banner(version: str = __version__, compact: bool = False) -> str:
    """Return the logo block, with version footer."""
    if compact:
        return f"{COMPACT}  v{version}\n"
    return f"{LOGO}                                                v{version}\n"
