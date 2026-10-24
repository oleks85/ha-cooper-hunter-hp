"""Cooper&Hunter heat pump (LinkedGo Modbus controller) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_BAUDRATE,
    CONF_PARAM_INTERVAL,
    CONF_PARITY,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    DEFAULT_BAUDRATE,
    DEFAULT_PARAM_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import HeatPumpCoordinator
from .modbus_client import ModbusClient

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.WATER_HEATER,
]

type HeatPumpConfigEntry = ConfigEntry[HeatPumpCoordinator]


def create_client(data: dict) -> ModbusClient:
    return ModbusClient(
        data[CONF_TRANSPORT],
        host=data.get(CONF_HOST),
        port=data.get(CONF_PORT),
        serial_port=data.get(CONF_SERIAL_PORT),
        baudrate=data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
        parity=data.get(CONF_PARITY, "N"),
        stopbits=data.get(CONF_STOPBITS, 1),
    )


async def async_setup_entry(hass: HomeAssistant, entry: HeatPumpConfigEntry) -> bool:
    client = create_client(dict(entry.data))
    coordinator = HeatPumpCoordinator(
        hass,
        entry,
        client,
        slave=entry.data[CONF_SLAVE],
        scan_interval=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        param_interval=entry.options.get(CONF_PARAM_INTERVAL, DEFAULT_PARAM_INTERVAL),
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await client.close()
        raise
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: HeatPumpConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HeatPumpConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.close()
    return unloaded
