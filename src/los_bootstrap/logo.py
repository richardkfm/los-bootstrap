"""ASCII logo printed on CLI startup.

Kept in its own module so it can be reused in docs and tests, and so the
exact glyphs are easy to find when someone wants to tweak the brand.
"""

from . import __version__

LOGO = r"""
          _____           _______                   _____
         /\    \         /::\    \                 /\    \
        /::\____\       /::::\    \               /::\    \
       /:::/    /      /::::::\    \             /::::\    \
      /:::/    /      /::::::::\    \           /::::::\    \
     /:::/    /      /:::/~~\:::\    \         /:::/\:::\    \
    /:::/    /      /:::/    \:::\    \       /:::/__\:::\    \
   /:::/    /      /:::/    / \:::\    \      \:::\   \:::\    \
  /:::/    /      /:::/____/   \:::\____\   ___\:::\   \:::\    \
 /:::/    /      |:::|    |     |:::|    | /\   \:::\   \:::\    \
/:::/____/       |:::|____|     |:::|    |/::\   \:::\   \:::\____\
\:::\    \        \:::\    \   /:::/    / \:::\   \:::\   \::/    /
 \:::\    \        \:::\    \ /:::/    /   \:::\   \:::\   \/____/
  \:::\    \        \:::\    /:::/    /     \:::\   \:::\    \
   \:::\    \        \:::\__/:::/    /       \:::\   \:::\____\
    \:::\    \        \::::::::/    /         \:::\  /:::/    /
     \:::\    \        \::::::/    /           \:::\/:::/    /
      \:::\    \        \::::/    /             \::::::/    /
       \:::\____\        \::/____/               \::::/    /
        \::/    /         ~~                      \::/    /
         \/____/                                   \/____/

                        +-+-+-+-+-+-+-+-+-+
                        |B|O|O|T|S|T|R|A|P|
                        +-+-+-+-+-+-+-+-+-+
"""

COMPACT = "« los · bootstrap »"


def banner(version: str = __version__, compact: bool = False) -> str:
    """Return the logo block, with version footer."""
    if compact:
        return f"{COMPACT}  v{version}\n"
    return f"{LOGO}                                                v{version}\n"
