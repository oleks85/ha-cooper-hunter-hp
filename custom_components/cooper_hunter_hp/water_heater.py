"""Water heater entity: domestic hot water (DHW)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_HEAT_PUMP,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, STATE_OFF, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatPumpConfigEntry
from .coordinator import HeatPumpCoordinator, encode
from .entity import HeatPumpEntity
from .modes import async_apply, dhw_enabled, space_mode
from .registers import REG_COMP_FREQ, REG_DHW_MAX, REG_DHW_MIN, REG_DHW_SET, REG_DHW_TANK, REG_MODE_STATE, Base


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatPumpConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([HeatPumpWaterHeater(entry.runtime_data)])


class HeatPumpWaterHeater(HeatPumpEntity, WaterHeaterEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_TENTHS
    _attr_operation_list = [STATE_OFF, STATE_HEAT_PUMP]
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )

    def __init__(self, coordinator: HeatPumpCoordinator) -> None:
        super().__init__(coordinator, "water_heater", Base(key="dhw", en="", uk=""))

    @property
    def current_operation(self) -> str:
        return STATE_HEAT_PUMP if dhw_enabled(self.coordinator) else STATE_OFF

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.value(REG_DHW_TANK, "temp")

    @property
    def target_temperature(self) -> float | None:
        return self.coordinator.value(REG_DHW_SET, "temp")

    @property
    def min_temp(self) -> float:
        value = self.coordinator.value(REG_DHW_MIN, "temp")
        return value if value is not None else 10

    @property
    def max_temp(self) -> float:
        value = self.coordinator.value(REG_DHW_MAX, "temp")
        return value if value is not None else 75

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "heating_now": data.get(REG_MODE_STATE) == 4 and (data.get(REG_COMP_FREQ) or 0) > 0,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self.coordinator.async_write(REG_DHW_SET, encode(temp, "temp"))

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        await async_apply(
            self.coordinator, space_mode(self.coordinator), operation_mode != STATE_OFF
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.async_set_operation_mode(STATE_HEAT_PUMP)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_operation_mode(STATE_OFF)
