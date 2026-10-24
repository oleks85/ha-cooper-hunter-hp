# Cooper&Hunter heat pump — Home Assistant integration (Modbus RS485)

Local Modbus integration for **Cooper&Hunter CH-HP15UIMPZM** air-to-water heat pumps and other units
built on the same **LinkedGo / WarmLink** controller (Kaisai, Phnix, Zealux, Aquatemp, Fairland, …;
register 1001–1006 contains a firmware id such as `WF220626 0313`).

Українською — нижче.

## Features

- Config flow (UI): Modbus TCP gateway, RTU‑over‑TCP (transparent gateway) or USB‑RS485 serial.
- ~220 entities: temperatures, compressor/fans, refrigerant circuit, electrical data, outputs/inputs,
  decoded fault bits (+ aggregated *Fault* / *Active faults*), runtime counters, energy.
- Control: `climate` (space heating/cooling), `water_heater` (DHW), power, operating mode, setpoints,
  weather curve, silent mode, pumps, electric heater, disinfection, hysteresis, manual defrost.
- Reads whole controller pages (5 requests per poll) and validates every response, so it works on a
  gateway shared with other Modbus masters.
- Stable, language‑independent entity ids: `<domain>.<prefix>_<key>` (default prefix `hp`).
- English and Ukrainian translations.
- Ready‑made dashboard: [`dashboard/heat_pump_dashboard.yaml`](dashboard/heat_pump_dashboard.yaml)
  (needs HACS cards *Mushroom* and *ApexCharts*).

## Wiring

RS485 **A/B** terminals of the heat pump → RS485 gateway (e.g. Elfin EW11, USR‑TCP232, Waveshare) or
USB adapter. Line settings: **9600 8N1**. Slave id = parameter *H10* (factory default 16, often 1).
Gateway mode: *Modbus TCP ⇄ RTU* → choose "Modbus TCP"; *transparent* → choose "RTU over TCP".

## Installation

1. HACS → Custom repositories → add `https://github.com/oleks85/ha-cooper-hunter-hp`
   (category *Integration*) → install,
   or copy `custom_components/cooper_hunter_hp` into `/config/custom_components/`.
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → *Cooper&Hunter Heat Pump (Modbus)*.
4. Optional dashboard: create a new dashboard → ⋮ → *Raw configuration editor* → paste
   `dashboard/heat_pump_dashboard.yaml`, or regenerate it with your own meters:

   ```bash
   python3 scripts/build_dashboard.py --power-meter sensor.my_power \
       --energy-meter sensor.my_energy --heat-meter sensor.my_heat_meter
   ```

## Notes

- The mode register combines space heating/cooling and DHW. `climate` and `water_heater` translate
  their on/off into the correct combined mode (e.g. turning DHW off in *DHW + heating* keeps heating).
- On CH-HP15UIMPZM the controller does not report water flow, power input, capacity or COP
  (registers 2054/2059/2060/2077 are always 0) — those entities are disabled by default. Use external
  meters for real COP.
- Bit meanings of 2019/2034/2081‑2089 follow the Cooper&Hunter user manual; unknown set bits are
  still reported in *Active faults* as `fault_<register>_bit<n>`.
- Full register table: [docs/REGISTERS.md](docs/REGISTERS.md).

## Development

```bash
pip install pytest-homeassistant-custom-component
pytest                       # tests run against an in‑process fake Modbus slave
python3 scripts/gen_translations.py   # after editing registers.py
python3 scripts/gen_docs.py
```

---

## Українською

Локальна інтеграція для теплового насоса **Cooper&Hunter CH-HP15UIMPZM** (контролер LinkedGo) через
RS485/Modbus. Підключення: клеми **A/B** насоса → RS485‑шлюз (Modbus TCP або прозорий режим) або
USB‑RS485; лінія **9600 8N1**, адреса — параметр H10.

Встановлення: HACS (власний репозиторій) або копіювання `custom_components/cooper_hunter_hp` у
`/config/custom_components/`, перезапуск HA, далі *Налаштування → Пристрої та служби → Додати
інтеграцію → Cooper&Hunter Heat Pump (Modbus)*.

Дашборд «Тепловий насос» (огляд, налаштування, діагностика) — у
[`dashboard/heat_pump_dashboard.yaml`](dashboard/heat_pump_dashboard.yaml); потрібні картки HACS
*Mushroom* та *ApexCharts*.
