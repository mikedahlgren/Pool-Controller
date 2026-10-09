# Pool Controller

This runs a pool from a [Waveshare ESP32-S3-RELAY-6CH](https://www.waveshare.com/esp32-s3-relay-6ch.htm) and the PoolVeras sensor hat plugged onto its Pico headers.

The Waveshare board talks to the pump, switches the acid pump and the pool light, and reports its own chip temperature. The hat is where the sensors connect: Atlas probe circuits, a 4-20 mA filter-pressure sender, optional pH current loop, DS18B20 temperature sensors, and dry contacts. Home Assistant and the page at `http://pool-controller.local` show the readings. Once an hour the controller can post pH and water temperature to PoolVeras.

## How the hardware is split

| Job | Board |
|-----|--------|
| Pentair IntelliFlo on RS485 | Waveshare, GPIO17 and GPIO18 |
| Acid pump | Waveshare relay CH2, GPIO2 |
| Pool light | Waveshare relay CH6, GPIO46 |
| Waterfall relay | Waveshare relay CH1, GPIO1. Leave it off unless you use it |
| Board temperature | Inside the ESP32-S3. This is the chip, not the pool |
| Atlas pH, ORP, salinity, RTD, or dissolved oxygen | Hat sockets. Any of those boards can go in any pair |
| Filter pressure and other 4-20 mA loops | Hat screw J8. Each loop needs its own 12 V or 24 V supply |
| Air and water temperature | Hat screw J6, DS18B20 sensors, one 4.7k shunt on JP6 |
| Dry contacts | Hat screw J7. A bare switch to the GND screw. ON means closed |

CH3, CH4, and CH5 on the Waveshare are free. The hat's 3.3 V rail, through fuse F1, powers the Atlas boards and the 1-Wire sensors. It does not power the 4-20 mA loops.

Screw order on the hat, left to right, is J3 through J8. Probe returns land on PGND next to PRB, not on the board ground screws.

Connector-by-connector wiring is in [esphome/README.md](esphome/README.md). Acid dosing is in [esphome/ACID_PH.md](esphome/ACID_PH.md). Filter pressure is in [esphome/FILTER_PRESSURE.md](esphome/FILTER_PRESSURE.md). The board files are in [hardware/sensor-hat](hardware/sensor-hat).

## Install

Use ESPHome 2025.9.0 or newer.

From Home Assistant, paste [`esphome/ha-pool-controller.yaml`](esphome/ha-pool-controller.yaml) into ESPHome Builder. It loads the rest of the firmware from the `PoolverasV1` branch. Copy the keys in [`esphome/secrets.yaml.example`](esphome/secrets.yaml.example) into Home Assistant's `secrets.yaml`, then Install.

From a clone of this repo:

```bash
esphome run esphome/pool-controller.yaml
```
