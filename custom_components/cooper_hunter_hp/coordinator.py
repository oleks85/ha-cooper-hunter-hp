"""Data coordinator for the Cooper&Hunter heat pump."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    FIRMWARE_REGS,
    MAX_STALE_POLLS,
    PAGE_HEADER_LEN,
    PARAM_BLOCKS,
    SENSOR_FAULT_VALUE,
    STATUS_BLOCKS,
)
from .modbus_client import ModbusClient, ModbusError

_LOGGER = logging.getLogger(__name__)

# Time the controller needs to apply a written parameter before it is re-read.
WRITE_SETTLE_DELAY = 1.0


def to_signed(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def decode(raw: dict[int, int], address: int, dtype: str) -> float | int | None:
    """Decode a register value according to the LinkedGo data types."""
    value = raw.get(address)
    if value is None:
        return None
    if dtype == "temp":
        if value == SENSOR_FAULT_VALUE:
            return None
        return round(to_signed(value) * 0.1, 1)
    if dtype == "s16":
        return to_signed(value)
    if dtype == "d5":
        return round(value * 0.1, 1)
    if dtype == "d9":
        return round(value * 0.01, 2)
    if dtype == "u32":
        low = raw.get(address + 1)
        if low is None:
            return None
        return (value << 16) | low
    return value


def encode(value: float, dtype: str) -> int:
    if dtype == "temp":
        return int(round(value * 10)) & 0xFFFF
    if dtype == "d5":
        return int(round(value * 10)) & 0xFFFF
    if dtype == "d9":
        return int(round(value * 100)) & 0xFFFF
    return int(round(value)) & 0xFFFF


class HeatPumpCoordinator(DataUpdateCoordinator[dict[int, int]]):
    """Polls the controller pages and serves writes."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: ModbusClient,
        slave: int,
        scan_interval: int,
        param_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
            always_update=False,
        )
        self.client = client
        self.slave = slave
        self._param_every = max(1, round(param_interval / scan_interval))
        self._poll_count = 0
        self._params_dirty = True
        self._failures = 0
        self._registers: dict[int, int] = {}
        self.firmware: str | None = None

    async def _read_block(self, start: int, count: int) -> dict[int, int]:
        values = await self.client.read_holding_registers(self.slave, start, count)
        # Every page carries its own start address in the header – cheap integrity check.
        if count >= PAGE_HEADER_LEN and values[PAGE_HEADER_LEN - 1] != start:
            raise ModbusError(f"Unexpected page header for block {start}: {values[:PAGE_HEADER_LEN]}")
        if self.firmware is None and count >= FIRMWARE_REGS[1]:
            chars = b"".join(v.to_bytes(2, "big") for v in values[FIRMWARE_REGS[0]:FIRMWARE_REGS[1]])
            self.firmware = chars.decode("ascii", "replace").strip("\x00 ") or None
        return {start + i: v for i, v in enumerate(values)}

    async def _async_update_data(self) -> dict[int, int]:
        blocks = list(STATUS_BLOCKS)
        read_params = self._params_dirty or self._poll_count % self._param_every == 0
        if read_params:
            blocks = list(PARAM_BLOCKS) + blocks
        self._poll_count += 1
        new: dict[int, int] = {}
        try:
            for start, count in blocks:
                new.update(await self._read_block(start, count))
        except ModbusError as err:
            self._failures += 1
            if self._registers and self._failures <= MAX_STALE_POLLS:
                _LOGGER.debug("Poll failed (%s/%s), keeping last data: %s",
                              self._failures, MAX_STALE_POLLS, err)
                self._registers.update(new)
                return dict(self._registers)
            raise UpdateFailed(f"Error communicating with heat pump: {err}") from err
        self._failures = 0
        if read_params:
            self._params_dirty = False
        self._registers.update(new)
        return dict(self._registers)

    async def async_write(self, address: int, value: int) -> None:
        """Write one holding register and refresh local state."""
        _LOGGER.debug("Writing %s -> register %s", value, address)
        try:
            await self.client.write_register(self.slave, address, value)
        except ModbusError as err:
            raise HomeAssistantError(f"Failed to write register {address}: {err}") from err
        self._registers[address] = value & 0xFFFF
        self.async_set_updated_data(dict(self._registers))
        self._params_dirty = True
        # Give the controller time to apply the change, then re-read everything.
        await asyncio.sleep(WRITE_SETTLE_DELAY)
        await self.async_request_refresh()

    async def async_write_many(self, values: dict[int, int]) -> None:
        for address, value in values.items():
            try:
                await self.client.write_register(self.slave, address, value)
            except ModbusError as err:
                raise HomeAssistantError(f"Failed to write register {address}: {err}") from err
            self._registers[address] = value & 0xFFFF
        self.async_set_updated_data(dict(self._registers))
        self._params_dirty = True
        await asyncio.sleep(WRITE_SETTLE_DELAY)
        await self.async_request_refresh()

    def value(self, address: int, dtype: str = "u16") -> Any:
        return decode(self.data or {}, address, dtype)
