"""Binary sensors for the Cooper&Hunter heat pump."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatPumpConfigEntry
from .coordinator import HeatPumpCoordinator
from .entity import HeatPumpEntity
from .registers import BINARY_SENSORS, DERIVED_BINARY, FAULT_REGISTERS, REG_COMP_FREQ, Base, BinaryDef


async def async_setup_entry(
    hass: HomeAssistant, entry: HeatPumpConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    derived = {d.key: d for d in DERIVED_BINARY}
    entities: list[BinarySensorEntity] = [RegisterBinarySensor(coordinator, d) for d in BINARY_SENSORS]
    entities += [
        CompressorRunningSensor(coordinator, derived["compressor_running"]),
        AnyFaultSensor(coordinator, derived["fault"]),
    ]
    async_add_entities(entities)


class RegisterBinarySensor(HeatPumpEntity, BinarySensorEntity):
    definition: BinaryDef

    def __init__(self, coordinator: HeatPumpCoordinator, definition: BinaryDef) -> None:
        super().__init__(coordinator, "binary_sensor", definition)
        if definition.device_class:
            self._attr_device_class = BinarySensorDeviceClass(definition.device_class)

    @property
    def is_on(self) -> bool | None:
        d = self.definition
        value = (self.coordinator.data or {}).get(d.address)
        if value is None:
            return None
        if d.bit is not None:
            return bool(value & (1 << d.bit)) != d.invert
        return value == d.equals


class CompressorRunningSensor(HeatPumpEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: HeatPumpCoordinator, definition: Base) -> None:
        super().__init__(coordinator, "binary_sensor", definition)

    @property
    def is_on(self) -> bool | None:
        freq = (self.coordinator.data or {}).get(REG_COMP_FREQ)
        return None if freq is None else freq > 0


class AnyFaultSensor(HeatPumpEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: HeatPumpCoordinator, definition: Base) -> None:
        super().__init__(coordinator, "binary_sensor", definition)

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data or {}
        return any(data.get(r) for r in FAULT_REGISTERS)
