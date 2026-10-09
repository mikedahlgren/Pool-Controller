# Pool Controller

ESPHome firmware for a [Waveshare ESP32-S3-RELAY-6CH](https://www.waveshare.com/esp32-s3-relay-6ch.htm) with the PoolVeras sensor hat on its Pico headers.

The hat is the sensor board. Relays and the pump RS485 stay on the Waveshare. How to wire each connector is in [esphome/README.md](esphome/README.md).

## Flash from Home Assistant

Copy one file into ESPHome Builder: [`esphome/ha-pool-controller.yaml`](esphome/ha-pool-controller.yaml). ESPHome pulls the rest from the `PoolverasV1` branch on GitHub when you install.

A local compile from a clone uses [`esphome/pool-controller.yaml`](esphome/pool-controller.yaml).

## What stays on the Waveshare

| Function | Where |
|----------|--------|
| Pentair IntelliFlo | RS485 terminals, GPIO17 and GPIO18 |
| Acid pump | Relay CH2, GPIO2 |
| Pool light | Relay CH6, GPIO46 |
| Waterfall output | Relay CH1, GPIO1. Leave it off unless you use it |
| Board temperature | Inside the ESP32-S3. This is the chip, not the air |

CH3, CH4, and CH5 are free.
