"""Diagnostics support."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import HeatPumpConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HeatPumpConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "firmware": coordinator.firmware,
        "registers": {str(k): v for k, v in sorted((coordinator.data or {}).items())},
    }
