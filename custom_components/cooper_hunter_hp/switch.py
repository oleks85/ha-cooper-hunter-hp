"""Switch entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatPumpConfigEntry
from .coordinator import HeatPumpCoordinator
from .entity import HeatPumpEntity
from .registers import SWITCHES, SwitchDef


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatPumpConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RegisterSwitch(coordinator, d) for d in SWITCHES)


class RegisterSwitch(HeatPumpEntity, SwitchEntity):
    definition: SwitchDef

    def __init__(self, coordinator: HeatPumpCoordinator, definition: SwitchDef) -> None:
        super().__init__(coordinator, "switch", definition)

    @property
    def is_on(self) -> bool | None:
        value = (self.coordinator.data or {}).get(self.definition.address)
        return None if value is None else value == self.definition.on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.definition.address, self.definition.on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self.definition.address, self.definition.off)
