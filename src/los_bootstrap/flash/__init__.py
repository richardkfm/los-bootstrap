"""Phase 8 — ROM flashing assistant.

Public API used by cli.py:

    from .flash import (
        DeviceState, Manufacturer,
        FlashPlan, FlashResult,
        Fastboot, FastbootNotFoundError, FastbootCommandError,
        Heimdall, heimdall_available,
        detect_manufacturer, detect_state,
        oem_unlock_enabled, developer_options_enabled,
        parse_rom_metadata,
        build_flash_plan,
        execute_flash_plan,
        unlock_guide, samsung_odin_guide,
        render_flash_status, render_flash_plan,
        render_verify_result, render_flash_result,
    )
"""

from .checks import (
    detect_manufacturer,
    detect_state,
    developer_options_enabled,
    is_ab_device,
    oem_unlock_enabled,
    parse_rom_metadata,
)
from .distros import (
    DistroFetchError,
    LineageBuild,
    alt_distro_links,
    download_lineage_zip,
    lineage_device_url,
    lookup_lineage_build,
)
from .fastboot import (
    Fastboot,
    FastbootCommandError,
    FastbootNotFoundError,
)
from .flash import execute_flash_plan
from .guide import samsung_odin_guide, unlock_guide
from .heimdall import Heimdall, HeimdallCommandError, HeimdallNotFoundError, heimdall_available
from .models import (
    DeviceState,
    FlashPlan,
    FlashResult,
    FlashStep,
    FlashStepKind,
    Manufacturer,
    RomMetadata,
)
from .plan import build_flash_plan
from .report import (
    render_download_options,
    render_flash_plan,
    render_flash_result,
    render_flash_status,
    render_verify_result,
)

__all__ = [
    "DeviceState",
    "Manufacturer",
    "FlashPlan",
    "FlashResult",
    "FlashStep",
    "FlashStepKind",
    "RomMetadata",
    "Fastboot",
    "FastbootCommandError",
    "FastbootNotFoundError",
    "Heimdall",
    "HeimdallCommandError",
    "HeimdallNotFoundError",
    "heimdall_available",
    "detect_manufacturer",
    "detect_state",
    "developer_options_enabled",
    "is_ab_device",
    "oem_unlock_enabled",
    "parse_rom_metadata",
    "DistroFetchError",
    "LineageBuild",
    "alt_distro_links",
    "download_lineage_zip",
    "lineage_device_url",
    "lookup_lineage_build",
    "build_flash_plan",
    "execute_flash_plan",
    "unlock_guide",
    "samsung_odin_guide",
    "render_download_options",
    "render_flash_status",
    "render_flash_plan",
    "render_verify_result",
    "render_flash_result",
]
