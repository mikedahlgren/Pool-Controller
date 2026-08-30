# ESPHome Components

## [pentair_if_ic](pentair_if_ic/README.md)

Controls a Pentair IntelliFlo variable-speed pump over RS485, and optionally a Pentair IntelliChlor on the same bus.

- Shared RS485 with bus arbitration
- Pump sensors and controls for Home Assistant
- IntelliChlor package is optional (`esphome/Include/chlorinator.yaml`); this install uses a CircuPool cell that does not speak that protocol

Home Assistant ESPHome Builder loads this from GitHub via `esphome/ha-pool-controller.yaml`. A local CLI compile uses `external_components` in `esphome/pool-controller.yaml`.
