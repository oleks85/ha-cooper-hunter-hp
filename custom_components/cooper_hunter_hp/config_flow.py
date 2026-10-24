"""Config flow for the Cooper&Hunter heat pump."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BAUDRATE,
    CONF_ENTITY_PREFIX,
    CONF_MODEL,
    CONF_PARAM_INTERVAL,
    CONF_PARITY,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    DEFAULT_BAUDRATE,
    DEFAULT_MODEL,
    DEFAULT_PARAM_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
    PAGE_HEADER_LEN,
    STATUS_BLOCKS,
)
from .modbus_client import TRANSPORT_RTU_OVER_TCP, TRANSPORT_SERIAL, TRANSPORT_TCP, ModbusError

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Heat pump"


async def validate_connection(data: dict[str, Any]) -> str | None:
    """Read the status page header; return firmware id or raise ModbusError."""
    from . import create_client  # noqa: PLC0415

    client = create_client(data)
    start = STATUS_BLOCKS[0][0]
    try:
        values = await client.read_holding_registers(data[CONF_SLAVE], start, PAGE_HEADER_LEN)
    finally:
        await client.close()
    if values[PAGE_HEADER_LEN - 1] != start:
        raise ModbusError("Device does not look like a LinkedGo heat pump controller")
    raw = b"".join(v.to_bytes(2, "big") for v in values[:6])
    return raw.decode("ascii", "replace").strip("\x00 ") or None


def _common_schema(defaults: dict[str, Any]) -> dict:
    return {
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
        vol.Required(CONF_MODEL, default=defaults.get(CONF_MODEL, DEFAULT_MODEL)): str,
        vol.Required(CONF_SLAVE, default=defaults.get(CONF_SLAVE, DEFAULT_SLAVE)): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
        vol.Optional(CONF_ENTITY_PREFIX, default=defaults.get(CONF_ENTITY_PREFIX, DEFAULT_PREFIX)): str,
    }


class HeatPumpConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._transport: str = TRANSPORT_TCP

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._transport = user_input[CONF_TRANSPORT]
            if self._transport == TRANSPORT_SERIAL:
                return await self.async_step_serial()
            return await self.async_step_network()
        schema = vol.Schema(
            {
                vol.Required(CONF_TRANSPORT, default=TRANSPORT_TCP): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[TRANSPORT_TCP, TRANSPORT_RTU_OVER_TCP, TRANSPORT_SERIAL],
                        translation_key="transport",
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_network(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**user_input, CONF_TRANSPORT: self._transport}
            await self.async_set_unique_id(f"{data[CONF_HOST]}:{data[CONF_PORT]}:{data[CONF_SLAVE]}")
            self._abort_if_unique_id_configured()
            result = await self._try_create(data, errors)
            if result:
                return result
        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                **_common_schema(defaults),
            }
        )
        return self.async_show_form(step_id="network", data_schema=schema, errors=errors)

    async def async_step_serial(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**user_input, CONF_TRANSPORT: TRANSPORT_SERIAL}
            await self.async_set_unique_id(f"{data[CONF_SERIAL_PORT]}:{data[CONF_SLAVE]}")
            self._abort_if_unique_id_configured()
            result = await self._try_create(data, errors)
            if result:
                return result
        defaults = user_input or {}
        schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT, default=defaults.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")): str,
                vol.Required(CONF_BAUDRATE, default=defaults.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)): vol.In(
                    [2400, 4800, 9600, 19200, 38400, 57600, 115200]
                ),
                vol.Required(CONF_PARITY, default=defaults.get(CONF_PARITY, "N")): vol.In(["N", "E", "O"]),
                vol.Required(CONF_STOPBITS, default=defaults.get(CONF_STOPBITS, 1)): vol.In([1, 2]),
                **_common_schema(defaults),
            }
        )
        return self.async_show_form(step_id="serial", data_schema=schema, errors=errors)

    async def _try_create(self, data: dict[str, Any], errors: dict[str, str]) -> ConfigFlowResult | None:
        try:
            await validate_connection(data)
        except ModbusError as err:
            _LOGGER.warning("Cannot connect to heat pump: %s", err)
            errors["base"] = "cannot_connect"
            return None
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error while validating heat pump connection")
            errors["base"] = "unknown"
            return None
        prefix = (data.get(CONF_ENTITY_PREFIX) or "").strip().lower()
        data[CONF_ENTITY_PREFIX] = prefix
        title = data.pop(CONF_NAME)
        return self.async_create_entry(title=title, data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HeatPumpOptionsFlow()


class HeatPumpOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=3, max=300)),
                vol.Required(
                    CONF_PARAM_INTERVAL, default=options.get(CONF_PARAM_INTERVAL, DEFAULT_PARAM_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
