"""Select entities (enumerated parameters)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatPumpConfigEntry
from .coordinator import HeatPumpCoordinator
from .entity import HeatPumpEntity
from .registers import SELECTS, SelectDef


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatPumpConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RegisterSelect(coordinator, d) for d in SELECTS)


class RegisterSelect(HeatPumpEntity, SelectEntity):
    definition: SelectDef

    def __init__(self, coordinator: HeatPumpCoordinator, definition: SelectDef) -> None:
        super().__init__(coordinator, "select", definition)
        self._attr_options = [o[0] for o in definition.options.values()]
        self._by_option = {o[0]: value for value, o in definition.options.items()}

    @property
    def current_option(self) -> str | None:
        value = (self.coordinator.data or {}).get(self.definition.address)
        option = self.definition.options.get(value) if value is not None else None
        return option[0] if option else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_write(self.definition.address, self._by_option[option])
