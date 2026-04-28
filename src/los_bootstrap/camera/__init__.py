"""Camera / GCam profile support — Phase 5 scaffold.

Intentionally not implemented. See `roadmap.md` Phase 5.

Planned scope:
- GCam port helper profiles, contributor-maintained per device
- LMC / XML config path guidance
- `los-bootstrap camera list-profiles` and `... show <profile>`
- Pre/post-apply verification steps
"""

from __future__ import annotations


def list_profiles(*_args, **_kwargs):
    """List known GCam helper profiles. Phase 5."""
    raise NotImplementedError(
        "camera.list_profiles is planned for Phase 5. See roadmap.md."
    )
