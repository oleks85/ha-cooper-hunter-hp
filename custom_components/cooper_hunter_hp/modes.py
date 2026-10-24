"""Shared helpers for the combined mode register (1012) and power (1011)."""

from __future__ import annotations

from .coordinator import HeatPumpCoordinator
from .registers import REG_MODE, REG_POWER

HEAT = "heat"
COOL = "cool"

_SPACE = {0: None, 1: HEAT, 2: COOL, 3: HEAT, 4: COOL}
_COMPOSE = {(None, True): 0, (HEAT, False): 1, (COOL, False): 2, (HEAT, True): 3, (COOL, True): 4}


def is_on(coordinator: HeatPumpCoordinator) -> bool:
    return (coordinator.data or {}).get(REG_POWER) == 1


def stored_mode(coordinator: HeatPumpCoordinator) -> int | None:
    return (coordinator.data or {}).get(REG_MODE)


def space_mode(coordinator: HeatPumpCoordinator) -> str | None:
    """Active space mode (heat/cool) or None, taking power into account."""
    if not is_on(coordinator):
        return None
    return _SPACE.get(stored_mode(coordinator))


def dhw_enabled(coordinator: HeatPumpCoordinator) -> bool:
    return is_on(coordinator) and stored_mode(coordinator) in (0, 3, 4)


async def async_apply(coordinator: HeatPumpCoordinator, space: str | None, dhw: bool) -> None:
    """Write mode/power so that the requested space+DHW combination is active."""
    mode = _COMPOSE.get((space, dhw))
    writes: dict[int, int] = {}
    if mode is None:
        writes[REG_POWER] = 0
    else:
        if stored_mode(coordinator) != mode:
            writes[REG_MODE] = mode
        if not is_on(coordinator):
            writes[REG_POWER] = 1
    if writes:
        await coordinator.async_write_many(writes)
