"""Base entity for the Cooper&Hunter heat pump."""

from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_ENTITY_PREFIX, CONF_MODEL, DEFAULT_MODEL, DEFAULT_PREFIX, DOMAIN, MANUFACTURER
from .coordinator import HeatPumpCoordinator
from .registers import REG_CODE_VERSION, REG_DISPLAY_VERSION, REG_MAINBOARD_VERSION, Base

CATEGORIES = {"diagnostic": EntityCategory.DIAGNOSTIC, "config": EntityCategory.CONFIG}


class HeatPumpEntity(CoordinatorEntity[HeatPumpCoordinator]):
    """Common entity: translated name, stable entity_id `<domain>.<prefix>_<key>`."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HeatPumpCoordinator, platform: str, definition: Base) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        prefix = entry.data.get(CONF_ENTITY_PREFIX, DEFAULT_PREFIX)
        self.definition = definition
        self._attr_translation_key = definition.key
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{definition.key}"
        self._attr_entity_registry_enabled_default = definition.enabled
        if definition.category:
            self._attr_entity_category = CATEGORIES[definition.category]
        if definition.icon:
            self._attr_icon = definition.icon
        if prefix:
            # Deterministic, language independent entity ids (HA UI may run in any language).
            self.entity_id = f"{platform}.{prefix}_{definition.key}"
        self._attr_device_info = device_info(coordinator)


def device_info(coordinator: HeatPumpCoordinator) -> DeviceInfo:
    entry = coordinator.config_entry
    data = coordinator.data or {}
    sw = []
    if coordinator.firmware:
        sw.append(coordinator.firmware)
    if (code := data.get(REG_CODE_VERSION)) is not None:
        sw.append(f"code {code / 10:.1f}")
    if (board := data.get(REG_MAINBOARD_VERSION)) is not None:
        sw.append(f"board {board}")
    hw = data.get(REG_DISPLAY_VERSION)
    return DeviceInfo(
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
        manufacturer=MANUFACTURER,
        model=entry.data.get(CONF_MODEL, DEFAULT_MODEL),
        name=entry.title,
        sw_version=", ".join(sw) or None,
        hw_version=f"display {hw}" if hw else None,
    )
