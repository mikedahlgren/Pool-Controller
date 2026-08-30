# Pool Controller

ESPHome firmware for a [Waveshare ESP32-S3-RELAY-6CH](https://www.waveshare.com/esp32-s3-relay-6ch.htm): Pentair IntelliFlo over onboard RS485, IntelliBrite-style lights, filter-tank pressure, Atlas industrial pH, and a Stenner acid pump.

Day-to-day UI is **Home Assistant** plus the device page at `http://pool-controller.local` (ESPHome `web_server` v3).

Upstream write-up: [ESPHome Pool Controller on the Home Assistant forums](https://community.home-assistant.io/t/esphome-pool-controller-integration-for-pentair-intelliflo-pumps-intellichlor-chlorinators-intellibrite-lights-and-other-pool-features/974565).

## Flash from Home Assistant

Copy **one file** into ESPHome Builder: [`esphome/ha-pool-controller.yaml`](esphome/ha-pool-controller.yaml). Do not upload this repository. ESPHome pulls `pentair_if_ic` and the Include YAMLs from GitHub at compile time.

Details: [esphome/README.md](esphome/README.md#home-assistant-esphome-builder-recommended).

## What this install drives

| Hardware | Connection |
|----------|------------|
| Pentair IntelliFlo | Isolated RS485 (GPIO17/18) |
| IntelliBrite-style lights | Relay CH6 (GPIO46) |
| Yosoo 4–20 mA filter pressure | Pico GP4 / GPIO4, 150 Ω shunt |
| Atlas Industrial pH Kit (KIT-102P) | Pico GP5 / GPIO5, dedicated 150 Ω shunt (4-wire) |
| Stenner 45M5 acid pump | Relay CH2 (GPIO2), hot only |
| Dallas air / water temp | 1-Wire GPIO10 |

CircuPool RJ-60 PLUS is **not** on the IntelliFlo bus. Pentair IntelliChlor YAML is optional (`chlorinator.yaml`, commented out).

Wiring: [esphome/README.md](esphome/README.md), [FILTER_PRESSURE.md](esphome/FILTER_PRESSURE.md), [ACID_PH.md](esphome/ACID_PH.md).

## Layout

- [`esphome/ha-pool-controller.yaml`](esphome/ha-pool-controller.yaml) — the file ESPHome Builder uses
- [`esphome/pool-controller.yaml`](esphome/pool-controller.yaml) — same firmware, local CLI compile from a clone
- [`esphome/Include/`](esphome/Include/) — packages pulled from GitHub
- [`components/pentair_if_ic`](components/pentair_if_ic) — IntelliFlo (and optional IntelliChlor) RS485 driver
