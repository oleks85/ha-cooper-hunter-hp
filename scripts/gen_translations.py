"""Generate strings.json and translations/{en,uk}.json from registers.py.

Usage: python3 scripts/gen_translations.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMP = ROOT / "custom_components" / "cooper_hunter_hp"

spec = importlib.util.spec_from_file_location("registers", COMP / "registers.py")
R = importlib.util.module_from_spec(spec)
sys.modules["registers"] = R
spec.loader.exec_module(R)  # type: ignore[union-attr]

CONFIG = {
    "en": {
        "user": ("Connection type", "How is the RS485 bus of the heat pump connected?",
                 {"transport": "Connection type"}),
        "network": ("RS485 gateway", "Modbus gateway connected to the RS485 A/B terminals of the heat pump.",
                    {"host": "Gateway IP / host", "port": "Port", "name": "Device name", "model": "Model",
                     "slave": "Modbus slave ID", "entity_prefix": "Entity ID prefix"}),
        "serial": ("Serial port", "USB-RS485 adapter connected to the heat pump.",
                   {"serial_port": "Serial port", "baudrate": "Baud rate", "parity": "Parity",
                    "stopbits": "Stop bits", "name": "Device name", "model": "Model",
                    "slave": "Modbus slave ID", "entity_prefix": "Entity ID prefix"}),
        "transport": {"tcp": "Modbus TCP gateway", "rtu_over_tcp": "RTU over TCP (transparent gateway)",
                      "serial": "Serial port (USB-RS485)"},
        "errors": {"cannot_connect": "Cannot read the heat pump. Check address, port, slave ID and gateway mode.",
                   "unknown": "Unexpected error"},
        "abort": {"already_configured": "This heat pump is already configured"},
        "options": ("Polling", {"scan_interval": "Status polling interval (s)",
                                "parameter_interval": "Parameter polling interval (s)"}),
    },
    "uk": {
        "user": ("Тип підключення", "Як підключено шину RS485 теплового насоса?",
                 {"transport": "Тип підключення"}),
        "network": ("Шлюз RS485", "Modbus-шлюз, підключений до клем RS485 A/B теплового насоса.",
                    {"host": "IP / адреса шлюзу", "port": "Порт", "name": "Назва пристрою", "model": "Модель",
                     "slave": "Modbus slave ID", "entity_prefix": "Префікс ID сутностей"}),
        "serial": ("Послідовний порт", "USB-RS485 адаптер, підключений до теплового насоса.",
                   {"serial_port": "Порт", "baudrate": "Швидкість", "parity": "Парність",
                    "stopbits": "Стоп-біти", "name": "Назва пристрою", "model": "Модель",
                    "slave": "Modbus slave ID", "entity_prefix": "Префікс ID сутностей"}),
        "transport": {"tcp": "Modbus TCP шлюз", "rtu_over_tcp": "RTU over TCP (прозорий шлюз)",
                      "serial": "Послідовний порт (USB-RS485)"},
        "errors": {"cannot_connect": "Не вдалося прочитати тепловий насос. Перевірте адресу, порт, slave ID і режим шлюзу.",
                   "unknown": "Неочікувана помилка"},
        "abort": {"already_configured": "Цей тепловий насос уже налаштовано"},
        "options": ("Опитування", {"scan_interval": "Інтервал опитування стану (с)",
                                   "parameter_interval": "Інтервал опитування параметрів (с)"}),
    },
}


def build(lang: str) -> dict:
    idx = 0 if lang == "en" else 1
    c = CONFIG[lang]

    def name(d):
        return d.en if lang == "en" else d.uk

    entity: dict[str, dict] = {k: {} for k in (
        "sensor", "binary_sensor", "number", "select", "switch", "button", "climate", "water_heater")}
    for d in R.SENSORS:
        item = {"name": name(d)}
        if d.options:
            item["state"] = {o[0]: o[1 + idx] for o in d.options.values()}
        entity["sensor"][d.key] = item
    for d in R.DERIVED_SENSORS:
        entity["sensor"][d.key] = {"name": name(d)}
    for d in R.BINARY_SENSORS + R.DERIVED_BINARY:
        entity["binary_sensor"][d.key] = {"name": name(d)}
    for d in R.NUMBERS:
        entity["number"][d.key] = {"name": name(d)}
    for d in R.SELECTS:
        entity["select"][d.key] = {"name": name(d),
                                   "state": {o[0]: o[1 + idx] for o in d.options.values()}}
    for d in R.SWITCHES:
        entity["switch"][d.key] = {"name": name(d)}
    for d in R.BUTTONS:
        entity["button"][d.key] = {"name": name(d)}
    entity["climate"]["heating"] = {"name": R.CLIMATE_NAME[idx]}
    entity["water_heater"]["dhw"] = {"name": R.WATER_HEATER_NAME[idx]}

    steps = {}
    for step in ("user", "network", "serial"):
        title, desc, data = c[step]
        steps[step] = {"title": title, "description": desc, "data": data}
    return {
        "config": {"step": steps, "error": c["errors"], "abort": c["abort"]},
        "options": {"step": {"init": {"title": c["options"][0], "data": c["options"][1]}}},
        "selector": {"transport": {"options": c["transport"]}},
        "entity": entity,
    }


def main() -> None:
    en = build("en")
    (COMP / "translations").mkdir(exist_ok=True)
    for path, content in ((COMP / "strings.json", en), (COMP / "translations" / "en.json", en),
                          (COMP / "translations" / "uk.json", build("uk"))):
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("wrote", path.relative_to(ROOT))
    keys = [d.key for d in R.SENSORS + R.DERIVED_SENSORS] + [d.key for d in R.BINARY_SENSORS + R.DERIVED_BINARY]
    assert len(set(d.key for d in R.SENSORS + R.DERIVED_SENSORS)) == len(R.SENSORS + R.DERIVED_SENSORS)
    assert len(set(d.key for d in R.BINARY_SENSORS + R.DERIVED_BINARY)) == len(R.BINARY_SENSORS + R.DERIVED_BINARY)
    print("entities:", len(keys) + len(R.NUMBERS) + len(R.SELECTS) + len(R.SWITCHES) + len(R.BUTTONS) + 2)


if __name__ == "__main__":
    main()
