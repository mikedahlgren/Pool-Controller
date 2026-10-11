# Waveshare ESP32-S3-RELAY-6CH pinout

This is the Waveshare board the hat plugs into. It is not the hat's screw map. Hat wiring is in [esphome/README.md](../esphome/README.md).

The stock module is ESP32-S3-WROOM-1U-N16: 16 MB flash and no PSRAM. GPIO35, GPIO36, and GPIO37 on J2 are free for the hat. A module with 8 MB octal PSRAM would take those three pins.

The Pico header is two 1x20 rows, 2.54 mm along a row and 17.78 mm between rows. It is not a Raspberry Pi 40-pin GPIO header. Pin 1 of each row is the antenna end. The USB edge is the other end of the rows.

On the hat, J1 is the USB-side row and J2 is the relay-side row. Both number pin 1 at the antenna. J1 pin N is Pico pin (41 - N). J2 pin N is Pico pin N.

Analog inputs on this chip are ADC1, GPIO1 through GPIO10, and ADC2, GPIO11 through GPIO20. ESPHome 2025.9 accepts both. GPIO1 and GPIO2 are relay drivers and are not on this header.

## Onboard functions

These are wired on the Waveshare board. Some of them also appear on the header.

| GPIO | Function |
|------|----------|
| GPIO0 | BOOT button. Strapping pin. |
| GPIO1 | Relay CH1 |
| GPIO2 | Relay CH2 |
| GPIO41 | Relay CH3 |
| GPIO42 | Relay CH4 |
| GPIO45 | Relay CH5. Strapping pin. |
| GPIO46 | Relay CH6. Strapping pin. |
| GPIO21 | Buzzer. Also J1 pin 20. |
| GPIO38 | RGB LED. Also J2 pin 17. |
| GPIO17 | RS485 TX. Also J2 pin 11. |
| GPIO18 | RS485 RX. Also J2 pin 12. |

## J1, USB row

Pico pins 40 down to 21. Hat socket J1. Pin 1 is the antenna end.

| J1 | Pico | Signal | Analog |
|----|------|--------|--------|
| 1 | 40 | 5 V | |
| 2 | 39 | VSYS | |
| 3 | 38 | GND | |
| 4 | 37 | 3.3 V | |
| 5 | 36 | 3.3 V | |
| 6 | 35 | GPIO10 | ADC1 |
| 7 | 34 | GPIO9 | ADC1 |
| 8 | 33 | GND | |
| 9 | 32 | GPIO8 | ADC1 |
| 10 | 31 | GPIO7 | ADC1 |
| 11 | 30 | 3.3 V | |
| 12 | 29 | GPIO6 | ADC1 |
| 13 | 28 | GND | |
| 14 | 27 | GPIO5 | ADC1 |
| 15 | 26 | GPIO4 | ADC1 |
| 16 | 25 | GPIO40 | |
| 17 | 24 | GPIO39 | |
| 18 | 23 | GND | |
| 19 | 22 | GPIO3 | ADC1. Strapping pin. |
| 20 | 21 | GPIO21 | Buzzer |

## J2, relay row

Pico pins 1 through 20. Hat socket J2. Pin 1 is the antenna end.

| J2 | Pico | Signal | Analog |
|----|------|--------|--------|
| 1 | 1 | GPIO43 | UART0 TX |
| 2 | 2 | GPIO44 | UART0 RX |
| 3 | 3 | GND | |
| 4 | 4 | GPIO13 | ADC2 |
| 5 | 5 | GPIO14 | ADC2 |
| 6 | 6 | GPIO15 | ADC2 |
| 7 | 7 | GPIO16 | ADC2 |
| 8 | 8 | GND | |
| 9 | 9 | GPIO47 | |
| 10 | 10 | GPIO48 | |
| 11 | 11 | GPIO17 | ADC2. RS485 TX. |
| 12 | 12 | GPIO18 | ADC2. RS485 RX. |
| 13 | 13 | GND | |
| 14 | 14 | GPIO35 | |
| 15 | 15 | GPIO36 | |
| 16 | 16 | GPIO37 | |
| 17 | 17 | GPIO38 | RGB LED |
| 18 | 18 | GND | |
| 19 | 19 | GPIO11 | ADC2 |
| 20 | 20 | GPIO12 | ADC2 |

GPIO43 and GPIO44 are the USB serial console. GPIO19 and GPIO20 are ADC2 as well, and they are the chip's USB pins. They are not on this header.
