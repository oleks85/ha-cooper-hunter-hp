"""Climate entity: space heating / cooling circuit."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatPumpConfigEntry
from .coordinator import HeatPumpCoordinator, encode
from .entity import HeatPumpEntity
from .modes import COOL, HEAT, async_apply, dhw_enabled, is_on, space_mode, stored_mode
from .registers import (
    REG_BUFFER,
    REG_COMP_FREQ,
    REG_COOL_MAX,
    REG_COOL_MIN,
    REG_COOL_SET,
    REG_HEAT_MAX,
    REG_HEAT_MIN,
    REG_HEAT_SET,
    REG_INLET,
    REG_MODE_STATE,
    REG_OUTLET,
    REG_ROOM,
    REG_TEMP_CONTROL,
    Base,
)

COOLING_ENABLED_REG = 1021
CONTROL_SOURCE = {0: REG_OUTLET, 1: REG_ROOM, 2: REG_BUFFER, 3: REG_INLET}


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatPumpConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([HeatPumpClimate(entry.runtime_data)])


class HeatPumpClimate(HeatPumpEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_TENTHS
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: HeatPumpCoordinator) -> None:
        super().__init__(coordinator, "climate", Base(key="heating", en="", uk=""))

    def _cooling_allowed(self) -> bool:
        return (self.coordinator.data or {}).get(COOLING_ENABLED_REG, 1) == 1

    @property
    def hvac_modes(self) -> list[HVACMode]:
        modes = [HVACMode.OFF, HVACMode.HEAT]
        if self._cooling_allowed():
            modes.append(HVACMode.COOL)
        return modes

    @property
    def hvac_mode(self) -> HVACMode:
        space = space_mode(self.coordinator)
        if space == HEAT:
            return HVACMode.HEAT
        if space == COOL:
            return HVACMode.COOL
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        data = self.coordinator.data or {}
        if not is_on(self.coordinator):
            return HVACAction.OFF
        state = data.get(REG_MODE_STATE)
        if state == 2:
            return HVACAction.DEFROSTING
        if (data.get(REG_COMP_FREQ) or 0) > 0:
            if state == 1:
                return HVACAction.HEATING
            if state == 0:
                return HVACAction.COOLING
        if space_mode(self.coordinator) is None:
            return HVACAction.OFF
        return HVACAction.IDLE

    def _is_cool_context(self) -> bool:
        return stored_mode(self.coordinator) in (2, 4)

    @property
    def current_temperature(self) -> float | None:
        source = (self.coordinator.data or {}).get(REG_TEMP_CONTROL, 0)
        return self.coordinator.value(CONTROL_SOURCE.get(source, REG_OUTLET), "temp")

    @property
    def target_temperature(self) -> float | None:
        reg = REG_COOL_SET if self._is_cool_context() else REG_HEAT_SET
        return self.coordinator.value(reg, "temp")

    @property
    def min_temp(self) -> float:
        reg = REG_COOL_MIN if self._is_cool_context() else REG_HEAT_MIN
        value = self.coordinator.value(reg, "temp")
        return value if value is not None else (5 if self._is_cool_context() else 15)

    @property
    def max_temp(self) -> float:
        reg = REG_COOL_MAX if self._is_cool_context() else REG_HEAT_MAX
        value = self.coordinator.value(reg, "temp")
        return value if value is not None else (28 if self._is_cool_context() else 75)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "dhw_enabled": dhw_enabled(self.coordinator),
            "heating_setpoint": self.coordinator.value(REG_HEAT_SET, "temp"),
            "cooling_setpoint": self.coordinator.value(REG_COOL_SET, "temp"),
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        space = {HVACMode.HEAT: HEAT, HVACMode.COOL: COOL}.get(hvac_mode)
        await async_apply(self.coordinator, space, dhw_enabled(self.coordinator))

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.COOL if self._is_cool_context() else HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_set_hvac_mode(mode)
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            reg = REG_COOL_SET if self._is_cool_context() else REG_HEAT_SET
            await self.coordinator.async_write(reg, encode(temp, "temp"))
