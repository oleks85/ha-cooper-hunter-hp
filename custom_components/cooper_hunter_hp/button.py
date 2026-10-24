"""Button entities."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatPumpConfigEntry
from .coordinator import HeatPumpCoordinator
from .entity import HeatPumpEntity
from .registers import BUTTONS, ButtonDef


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatPumpConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(BitButton(coordinator, d) for d in BUTTONS)


class BitButton(HeatPumpEntity, ButtonEntity):
    """Sets a command bit in a bitfield register (controller clears it itself)."""

    definition: ButtonDef

    def __init__(self, coordinator: HeatPumpCoordinator, definition: ButtonDef) -> None:
        super().__init__(coordinator, "button", definition)

    async def async_press(self) -> None:
        d = self.definition
        current = (self.coordinator.data or {}).get(d.address, 0)
        await self.coordinator.async_write(d.address, current | (1 << d.bit))
