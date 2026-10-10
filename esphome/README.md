# Sensor hat

The hat plugs onto the Waveshare Pico headers. Screw connectors run along the edge, left to right: **J3, J4, J5, J6, J7, J8**.

Relays and the pump cable stay on the Waveshare. See [the repo README](../README.md).

## Atlas circuit boards

Three pairs of sockets. The silk says pH, ORP, and EZO so the installer can tell them apart. Any Atlas circuit can go in any pair: pH, ORP, conductivity (salinity), RTD, or dissolved oxygen.

Each circuit uses both sockets in its pair.

- The socket nearer the screws is power: VCC, PRB, PGND.
- The socket farther from the screws is data: GND, TX, RX. Pin 1 of that socket is ground.

The probe cable lands on the two screws under that pair.

| Pair | Screws | Probe screws, left to right |
|------|--------|-----------------------------|
| Labeled pH | J3 | PRB, PGND |
| Labeled ORP | J4 | PRB, PGND |
| Labeled EZO | J5 | PRB, PGND |

PRB is the probe signal. PGND is that probe's return. PGND is not the ground screw on J6 or J7. Leave the probe return on PGND.

Factory boards on the pairs labeled pH and ORP speak UART and answer as soon as they are seated. The device page shows what each socket found: pH Socket, ORP Socket, EZO Socket. Readings show up as EZO pH, ORP, Conductivity, Salinity, TDS, RTD Temperature, or Dissolved Oxygen, based on the board, not the label.

A board that was already switched to I2C still works in any socket. Two of the same type: the reading comes from the first socket that has one, in the order pH label, ORP label, EZO label.

The third pair (labeled EZO) is the I2C bus, shared with J16. J16 is a female 4-pin socket for a 2.42 inch SSD1309. Pin order, from the left: GND, 3V3, SCL, SDA. The screen address is 0x3C. Solder the socket and plug the display in with its GND pin on the left. A factory UART board on that pair will fight the screen, so switch that Atlas board to I2C on one of the other pairs first. Atlas defaults are 99 (pH), 98 (ORP), and 100 (EC).

## pH

Pool pH is the value used for acid dosing and PoolVeras. On the device page, **pH Source** chooses it:

| Setting | What Pool pH uses |
|---------|-------------------|
| Auto | The Atlas pH board, if one is answering. Otherwise the 4-20 mA kit. |
| EZO | The Atlas pH board only. |
| 4-20 mA | The industrial kit on J8 screw 2 only. |

`ph_offset` trims only the 4-20 mA reading. Calibrate an Atlas pH board on the module.

Acid dosing behavior is in [ACID_PH.md](ACID_PH.md).

## 4-20 mA (J8)

Left to right: GND, 1, 2, 3, 4.

Each signal screw already has a 150 ohm resistor to the GND screw, plus a filter and a clamp. Do not add another shunt.

These loops need their own DC supply, usually 12 V or 24 V, inside the transmitter's range. Do not power them from the hat's 3.3 V pin.

For each channel:

1. Supply positive to the transmitter positive.
2. Transmitter negative to that channel's signal screw.
3. Supply negative to the GND screw.

One supply can feed all four channels. Split the positive side. Each transmitter returns on its own signal screw.

| Screw | What the firmware does |
|-------|------------------------|
| 1 | Filter pressure. GPIO7. Default range 0 to 0.5 MPa. See [FILTER_PRESSURE.md](FILTER_PRESSURE.md). |
| 2 | Industrial pH kit, 4 mA = 0 pH, 20 mA = 14 pH. GPIO8. |
| 3 | Milliamps only. GPIO9. |
| 4 | Milliamps only. GPIO10. |

At 20 mA the 150 ohm resistor is 3.0 V. The ESP32-S3 analog input is soft above about 2.5 V, which is about 16 mA. Normal pool pressure and pH sit under that. The top of the scale reads a little low. The 150 ohm parts stay as they are.

Do not land a fault wire from the Atlas industrial transmitter on the hat. That output is 12 to 24 V.

## 1-Wire (J6)

Left to right: 3V3, DATA, GND. The data pin is GPIO37.

This is for DS18B20 sensors. Air and water can share the three screws. Fit **one** shunt on JP6. Use the 4.7k position for these sensors. The 2.2k and 1k positions are the other choices. Do not fit more than one.

After the first boot, copy each sensor's address from the ESPHome log into `secrets.yaml` as `air_temp_id` and `water_temp_id`.

**Board Temperature** is separate. It is the ESP32-S3 chip, in °F. It rises when WiFi is busy. It is not a stand-in for the air or water sensor.

## Contacts (J7)

Left to right: GND, 1, 2, 3, 4.

Each input is a dry contact: a switch with no voltage of its own. One side goes to a numbered screw. The other side goes to the GND screw on J7. ON means that switch is closed.

| Screw | GPIO |
|-------|------|
| 1 | GPIO47 |
| 2 | GPIO16 |
| 3 | GPIO14 |
| 4 | GPIO13 |

Do not connect a powered switch output (5 V, 12 V, or 24 V). The clamp will hold the pin in a safe range and dump the extra current onto the 3.3 V rail.

## Power on the hat

The hat takes 3.3 V from the Waveshare header, through fuse F1 (0.2 A). That rail runs the Atlas circuits, the 1-Wire sensors, and the pull-ups. It does not run 4-20 mA loops.

## Install

Home Assistant: paste [`ha-pool-controller.yaml`](ha-pool-controller.yaml) into ESPHome Builder. It loads the packages from the `PoolverasV1` branch. Add the keys in [`secrets.yaml.example`](secrets.yaml.example) to Home Assistant's `secrets.yaml`, then Install.

From a clone, at the repo root:

```bash
esphome run esphome/pool-controller.yaml
```

The device page is `http://pool-controller.local`.

ESPHome 2025.9.0 or newer. The custom pieces are `pentair_if_ic` (the pump) and `atlas_ezo` (the three sockets).
