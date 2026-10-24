"""Number entities (setpoints and parameters)."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatPumpConfigEntry
from .coordinator import HeatPumpCoordinator, encode
from .entity import HeatPumpEntity
from .registers import NUMBERS, NumberDef


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatPumpConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RegisterNumber(coordinator, d) for d in NUMBERS)


class RegisterNumber(HeatPumpEntity, NumberEntity):
    definition: NumberDef

    def __init__(self, coordinator: HeatPumpCoordinator, definition: NumberDef) -> None:
        super().__init__(coordinator, "number", definition)
        self._attr_native_step = definition.step
        self._attr_native_unit_of_measurement = definition.unit
        self._attr_mode = NumberMode(definition.mode)
        if definition.device_class:
            self._attr_device_class = NumberDeviceClass(definition.device_class)

    @property
    def native_min_value(self) -> float:
        d = self.definition
        if d.min_reg is not None and (v := self.coordinator.value(d.min_reg, d.dtype)) is not None:
            return max(d.min, v)
        return d.min

    @property
    def native_max_value(self) -> float:
        d = self.definition
        if d.max_reg is not None and (v := self.coordinator.value(d.max_reg, d.dtype)) is not None:
            return min(d.max, v)
        return d.max

    @property
    def native_value(self) -> float | None:
        return self.coordinator.value(self.definition.address, self.definition.dtype)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write(self.definition.address, encode(value, self.definition.dtype))
