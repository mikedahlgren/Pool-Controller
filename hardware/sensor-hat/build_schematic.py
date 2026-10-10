#!/usr/bin/env python3
"""Schematic for the pool sensor hat. Does not place or route the PCB."""

import math
import re
import uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent
SHEET = str(uuid.uuid5(uuid.NAMESPACE_URL, "pool-sensor-hat-root"))
PROJECT = "sensor-hat"

LIB = {
    "Device:R": "/usr/share/kicad/symbols/Device.kicad_sym",
    "Device:C": "/usr/share/kicad/symbols/Device.kicad_sym",
    "Device:D_Zener": "/usr/share/kicad/symbols/Device.kicad_sym",
    "Device:Polyfuse": "/usr/share/kicad/symbols/Device.kicad_sym",
    "Diode:BAT54S": "/usr/share/kicad/symbols/Diode.kicad_sym",
    "power:GND": "/usr/share/kicad/symbols/power.kicad_sym",
    "power:+3V3": "/usr/share/kicad/symbols/power.kicad_sym",
    "power:PWR_FLAG": "/usr/share/kicad/symbols/power.kicad_sym",
    "Connector_Generic:Conn_01x02": "/usr/share/kicad/symbols/Connector_Generic.kicad_sym",
    "Connector_Generic:Conn_01x03": "/usr/share/kicad/symbols/Connector_Generic.kicad_sym",
    "Connector_Generic:Conn_01x04": "/usr/share/kicad/symbols/Connector_Generic.kicad_sym",
    "Connector_Generic:Conn_01x05": "/usr/share/kicad/symbols/Connector_Generic.kicad_sym",
    "Connector_Generic:Conn_01x20": "/usr/share/kicad/symbols/Connector_Generic.kicad_sym",
    "Connector_Generic:Conn_02x03_Odd_Even": "/usr/share/kicad/symbols/Connector_Generic.kicad_sym",
    "Switch:SW_Push": "/usr/share/kicad/symbols/Switch.kicad_sym",
}

FP_R = "PCM_JLCPCB:R_0805"
FP_C = "PCM_JLCPCB:C_0805"
FP_SOT = "Package_TO_SOT_SMD:SOT-23"
FP_FUSE = "Fuse:Fuse_1812_4532Metric"
FP_JUMP = "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
FP_JUMP6 = "Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical"
FP_SOCK = "Connector_PinSocket_2.54mm:PinSocket_1x20_P2.54mm_Vertical"
FP_EZO = "Connector_PinSocket_2.54mm:PinSocket_1x03_P2.54mm_Vertical"
FP_MC = "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5_{n}-5.08_1x0{n}_P5.08mm_Horizontal"

LCSC = {
    "150": "C17471",
    "1k": "C17513",
    "10k": "C17414",
    "4.7k": "C17673",
    "2.2k": "C17520",
    "100": "C17408",
    "100n": "C28233",
    "10u": "C15850",
    "BAT54S": "C7420333",
}


def uid():
    return str(uuid.uuid4())


def snap(value):
    """KiCad's schematic connection grid is 1.27 mm."""
    return round(round(value / 1.27) * 1.27, 2)


def extract_symbol(path, name):
    text = Path(path).read_text(errors="replace")
    token = f'(symbol "{name}"'
    i = text.find(token)
    if i < 0:
        raise SystemExit(f"missing symbol {name} in {path}")
    depth = 0
    for j, ch in enumerate(text[i:], i):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[i : j + 1]
    raise SystemExit(f"unbalanced {name}")


def unit_pins(block):
    import re

    m = re.search(r'\(symbol "[^"]+_1_1"', block)
    if not m:
        sub = block
    else:
        start = m.start()
        depth = 0
        for j, ch in enumerate(block[start:], start):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    sub = block[start : j + 1]
                    break
    pins = {}
    i = 0
    while True:
        k = sub.find("(pin ", i)
        if k < 0:
            break
        depth = 0
        for j, ch in enumerate(sub[k:], k):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    pin = sub[k : j + 1]
                    break
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+) (\d+)\)", pin)
        num = re.search(r'\(number "([^"]*)"', pin)
        pins[num.group(1)] = (float(at.group(1)), float(at.group(2)), int(at.group(3)))
        i = j + 1
    return pins


def rename_symbol(block, lib_id):
    name = lib_id.split(":", 1)[1]
    old = f'(symbol "{name}"'
    new = f'(symbol "{lib_id}"'
    if not block.startswith(old):
        raise SystemExit(f"rename failed for {lib_id}")
    return new + block[len(old) :]


def rename_pins(block, names):
    for i, label in enumerate(names, start=1):
        old = f'(name "Pin_{i}"'
        new = f'(name "{label}"'
        if old not in block:
            raise SystemExit(f"missing {old}")
        block = block.replace(old, new, 1)
    return block


class Sch:
    def __init__(self):
        self.raw_syms = {}
        self.pins = {}
        self.parts = []
        self.wires = []
        self.labels = []
        self.ncs = []
        self.texts = []
        self.bom = []
        self.pwr = 0
        self.flg = 0
        for lib_id, path in LIB.items():
            name = lib_id.split(":", 1)[1]
            block = extract_symbol(path, name)
            self.pins[lib_id] = unit_pins(block)
            self.raw_syms[lib_id] = rename_symbol(block, lib_id)
        v3 = self.raw_syms["power:+3V3"].replace("+3V3", "V3OUT")
        self.raw_syms["power:V3OUT"] = v3
        self.pins["power:V3OUT"] = dict(self.pins["power:+3V3"])

    def clone_symbol(self, src, lib_id, pin_names, pin_at=None):
        sym_name = lib_id.split(":", 1)[1]
        src_name = src.split(":", 1)[1]
        block = self.raw_syms[src]
        block = block.replace(f'(symbol "{src}"', f'(symbol "{lib_id}"', 1)
        block = block.replace(f'(symbol "{src_name}_', f'(symbol "{sym_name}_')
        block = rename_pins(block, pin_names)
        block = re.sub(
            r"\(pin_names(\s*)\(offset 1\.016\)(\s*)\(hide yes\)",
            r"(pin_names\1(offset 1.016)\2(hide no)",
            block,
            count=1,
        )
        def at_text(coords):
            parts = []
            for value in coords:
                number = float(value)
                parts.append(str(int(number)) if number == int(number) else str(number))
            return "(at " + " ".join(parts) + ")"

        pins = {num: coords for num, coords in self.pins[src].items()}
        if pin_at:
            for num, at in pin_at.items():
                old = at_text(pins[num])
                new = at_text(at)
                if old not in block:
                    raise SystemExit(f"missing {old} in {lib_id}")
                block = block.replace(old, new, 1)
                pins[num] = at
        self.raw_syms[lib_id] = block
        self.pins[lib_id] = pins

    def custom_header(self, lib_id, names):
        sym_name = lib_id.split(":", 1)[1]
        block = rename_pins(self.raw_syms["Connector_Generic:Conn_01x20"], names)
        block = block.replace('(symbol "Connector_Generic:Conn_01x20"', f'(symbol "{lib_id}"', 1)
        block = block.replace('(symbol "Conn_01x20_', f'(symbol "{sym_name}_')
        block = re.sub(
            r"\(pin_names(\s*)\(offset 1\.016\)(\s*)\(hide yes\)",
            r"(pin_names\1(offset 1.016)\2(hide no)",
            block,
            count=1,
        )
        self.raw_syms[lib_id] = block
        self.pins[lib_id] = self.pins["Connector_Generic:Conn_01x20"]

    def add_box(self, lib_id, title, right, left=(), width=50.8):
        """One schematic block. right and left are (name, sheet_dy) from the top pin.

        sheet_dy is 0 at the top pin and negative below it. Pins land on the
        right and left edges. The placed symbol origin is the top right pin.
        """
        sym = lib_id.split(":", 1)[1]
        pins = {}
        chunks = []
        number = 1
        lib_ys = []

        def add_pin(name, sheet_dy, x, angle, num):
            lib_y = -sheet_dy
            lib_ys.append(lib_y)
            pins[str(num)] = (x, lib_y, angle)
            chunks.append(
                "\t\t(pin passive line\n"
                f"\t\t\t(at {x} {lib_y} {angle})\n"
                "\t\t\t(length 2.54)\n"
                f'\t\t\t(name "{name}"\n'
                "\t\t\t\t(effects (font (size 1.27 1.27)))\n"
                "\t\t\t)\n"
                f'\t\t\t(number "{num}"\n'
                "\t\t\t\t(effects (font (size 1.27 1.27)))\n"
                "\t\t\t)\n"
                "\t\t)"
            )

        def walk(entries, x, angle):
            nonlocal number
            for entry in entries:
                if len(entry) == 3:
                    name, sheet_dy, num = entry
                else:
                    name, sheet_dy = entry
                    num = number
                    number += 1
                add_pin(name, sheet_dy, x, angle, num)

        walk(right, 0, 180)
        walk(left, -width, 0)
        top = min(lib_ys) - 5.08
        bot = max(lib_ys) + 5.08
        body = (
            f'\t\t(rectangle (start {-width} {top}) (end -2.54 {bot})\n'
            "\t\t\t(stroke (width 0.254) (type default))\n"
            "\t\t\t(fill (type background)))\n"
            f'\t\t(text "{title}" (at {-width / 2} {top + 2.54} 0)\n'
            "\t\t\t(effects (font (size 1.27 1.27))))"
        )
        block = (
            f'(symbol "{lib_id}"\n'
            "\t(pin_numbers (hide yes))\n"
            "\t(pin_names (offset 1.016))\n"
            "\t(exclude_from_sim no)\n"
            "\t(in_bom no)\n"
            "\t(on_board no)\n"
            f'\t(property "Reference" "U" (at {-width / 2} {top - 2.54} 0)\n'
            "\t\t(effects (font (size 1.27 1.27))))\n"
            f'\t(property "Value" "{title}" (at {-width / 2} {bot + 2.54} 0)\n'
            "\t\t(effects (font (size 1.27 1.27))))\n"
            '\t(property "Footprint" "" (at 0 0 0)\n'
            "\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n"
            '\t(property "Datasheet" "" (at 0 0 0)\n'
            "\t\t(effects (font (size 1.27 1.27)) (hide yes)))\n"
            f'\t(symbol "{sym}_0_1"\n{body}\n\t)\n'
            f'\t(symbol "{sym}_1_1"\n' + "\n".join(chunks) + "\n\t)\n"
            "\t(embedded_fonts no)\n"
            ")"
        )
        self.raw_syms[lib_id] = block
        self.pins[lib_id] = pins

    def place(self, lib_id, ref, value, x, y, footprint="", extra=None, rot=0, bom=True, dnp=False):
        # A placed symbol mirrors the library Y axis, then rotates.
        x, y = snap(x), snap(y)
        extra = dict(extra or {})
        ref_at = extra.pop("ref_at", None)
        val_at = extra.pop("val_at", None)
        world = {}
        rad = math.radians(rot)
        c, s = math.cos(rad), math.sin(rad)
        for num, (px, py, ang) in self.pins[lib_id].items():
            lx, ly = px, -py
            rx = lx * c - ly * s
            ry = lx * s + ly * c
            vx = math.cos(math.radians(ang))
            vy = -math.sin(math.radians(ang))
            wx = vx * c - vy * s
            wy = vx * s + vy * c
            world_ang = round(math.degrees(math.atan2(wy, wx))) % 360
            world[num] = (round(x + rx, 2), round(y + ry, 2), world_ang)
        self.parts.append(
            {
                "lib_id": lib_id,
                "ref": ref,
                "value": value,
                "footprint": footprint,
                "x": x,
                "y": y,
                "rot": rot,
                "extra": extra,
                "pins": world,
                "bom": bom,
                "dnp": dnp,
                "ref_at": ref_at,
                "val_at": val_at,
            }
        )
        if bom and not dnp and not ref.startswith("#"):
            lcsc = (extra or {}).get("LCSC", "")
            self.bom.append((ref, value, footprint, lcsc))
        return world

    def wire(self, x1, y1, x2, y2):
        x1, y1, x2, y2 = (round(v, 2) for v in (x1, y1, x2, y2))
        if (x1, y1) != (x2, y2):
            self.wires.append((x1, y1, x2, y2))

    def stub(self, x, y, ang, length=5.08):
        rad = math.radians(ang + 180)
        x2 = round(x + length * math.cos(rad), 2)
        y2 = round(y + length * math.sin(rad), 2)
        self.wire(x, y, x2, y2)
        return x2, y2

    def label(self, name, x, y, grow="right"):
        self.labels.append((name, round(x, 2), round(y, 2), grow))

    def nc(self, x, y):
        self.ncs.append((round(x, 2), round(y, 2)))

    def text(self, body, x, y, size=1.27):
        self.texts.append((body, round(x, 2), round(y, 2), size))

    def tie(self, pin, net, length=5.08):
        x, y, ang = pin
        ex, ey = self.stub(x, y, ang, length)
        if net == "GND":
            self.pwr += 1
            self.place("power:GND", f"#PWR{self.pwr:03d}", "GND", ex, ey, bom=False)
        elif net in ("+3V3", "V3OUT"):
            self.pwr += 1
            self.place(f"power:{net}", f"#PWR{self.pwr:03d}", net, ex, ey, bom=False)
        else:
            grow = "left" if math.cos(math.radians(ang + 180)) < 0 else "right"
            self.label(net, ex, ey, grow)
        return ex, ey

    def flag(self, x, y):
        self.flg += 1
        self.place("power:PWR_FLAG", f"#FLG{self.flg:02d}", "PWR_FLAG", x, y, bom=False)

    def emit(self, path):
        L = []
        w = L.append
        w("(kicad_sch")
        w("\t(version 20250114)")
        w('\t(generator "eeschema")')
        w('\t(generator_version "9.0")')
        w(f'\t(uuid "{SHEET}")')
        w('\t(paper "A1")')
        w("\t(title_block")
        w('\t\t(title "Pool sensor hat")')
        w('\t\t(date "2026-10-06")')
        w('\t\t(rev "1")')
        w('\t\t(company "Pool-Controller")')
        w('\t\t(comment 1 "P1 is J1 and J2, the two Pico sockets, one Waveshare interface.")')
        w('\t\t(comment 2 "U1, U2, and U3 are the plug-in EZO boards. PGND is not GND.")')
        w('\t\t(comment 3 "Signal nets are wired. Power and ground use symbols.")')
        w('\t\t(comment 4 "J1 pins 4 and 5 are 3.3 V on the Waveshare and are open on this hat.")')
        w("\t)")
        w("\t(lib_symbols")
        for lib_id, block in self.raw_syms.items():
            for line in block.splitlines():
                w("\t" + line)
        w("\t)")
        for part in self.parts:
            self._emit_part(w, part)
        for x1, y1, x2, y2 in self.wires:
            w("\t(wire")
            w("\t\t(pts")
            w(f"\t\t\t(xy {x1} {y1})")
            w(f"\t\t\t(xy {x2} {y2})")
            w("\t\t)")
            w("\t\t(stroke (width 0) (type solid))")
            w(f'\t\t(uuid "{uid()}")')
            w("\t)")
        for name, x, y, grow in self.labels:
            just = "right" if grow == "left" else "left"
            w("\t(label " + _q(name))
            w(f"\t\t(at {x} {y} 0)")
            w("\t\t(effects (font (size 1.27 1.27)) (justify " + just + " bottom))")
            w(f'\t\t(uuid "{uid()}")')
            w("\t)")
        for x, y in self.ncs:
            w("\t(no_connect")
            w(f"\t\t(at {x} {y})")
            w(f'\t\t(uuid "{uid()}")')
            w("\t)")
        for body, x, y, size in self.texts:
            w("\t(text " + _q(body))
            w("\t\t(exclude_from_sim no)")
            w(f"\t\t(at {x} {y} 0)")
            w("\t\t(effects (font (size " + f"{size} {size}" + ")))")
            w(f'\t\t(uuid "{uid()}")')
            w("\t)")
        w("\t(sheet_instances")
        w('\t\t(path "/"')
        w('\t\t\t(page "1")')
        w("\t\t)")
        w("\t)")
        w("\t(embedded_fonts no)")
        w(")")
        path.write_text("\n".join(L) + "\n")

    def _emit_part(self, w, part):
        x, y = part["x"], part["y"]
        power = part["lib_id"].startswith("power:")
        fitted = part["bom"] and not part.get("dnp")
        on_board = "yes" if part["bom"] or part.get("dnp") else "no"
        in_bom = "yes" if fitted else "no"
        w("\t(symbol")
        w(f'\t\t(lib_id "{part["lib_id"]}")')
        w(f'\t\t(at {x} {y} {part["rot"]})')
        w("\t\t(unit 1)")
        w("\t\t(exclude_from_sim no)")
        w(f'\t\t(in_bom {in_bom})')
        w(f'\t\t(on_board {on_board})')
        w(f'\t\t(dnp {"yes" if part.get("dnp") else "no"})')
        w(f'\t\t(uuid "{uid()}")')
        ref_at = part["ref_at"] or (x + 6.35, y + 3.81)
        val_at = part["val_at"] or (x + 6.35, y - 3.81)
        fields = [
            ("Reference", part["ref"], ref_at[0], ref_at[1], power),
            ("Value", part["value"], val_at[0], val_at[1], False),
            ("Footprint", part["footprint"], x, y, True),
            ("Datasheet", part["extra"].get("Datasheet", ""), x, y, True),
        ]
        for key, val in part["extra"].items():
            if key in ("Reference", "Value", "Footprint", "Datasheet"):
                continue
            fields.append((key, val, x, y, True))
        for key, val, px, py, hide in fields:
            w(f"\t\t(property \"{key}\" {_q(val)}")
            w(f"\t\t\t(at {px} {py} 0)")
            if hide:
                w("\t\t\t(effects (font (size 1.27 1.27)) (hide yes))")
            else:
                w("\t\t\t(effects (font (size 1.27 1.27)))")
            w("\t\t)")
        for num in part["pins"]:
            w(f'\t\t(pin "{num}"')
            w(f'\t\t\t(uuid "{uid()}")')
            w("\t\t)")
        w("\t\t(instances")
        w(f'\t\t\t(project "{PROJECT}"')
        w(f'\t\t\t\t(path "/{SHEET}"')
        w(f'\t\t\t\t\t(reference "{part["ref"]}")')
        w("\t\t\t\t\t(unit 1)")
        w("\t\t\t\t)")
        w("\t\t\t)")
        w("\t\t)")
        w("\t)")


def _q(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


PITCH = 15.24
GAP = 30.48
TOP = 40.0


def r_extra(value):
    return {"LCSC": LCSC[value], "Tolerance": "1%"}


def build():
    sch = Sch()
    sch.bom.append(("J1", "Pin socket 1x20 back side", FP_SOCK, ""))
    sch.bom.append(("J2", "Pin socket 1x20 back side", FP_SOCK, ""))

    groups = [
        [("3V3  J1.11", "3V3")],
        [
            ("ADC1  GPIO7", "ADC1"),
            ("ADC2  GPIO8", "ADC2"),
            ("ADC3  GPIO9", "ADC3"),
            ("ADC4  GPIO10", "ADC4"),
        ],
        [
            ("DIN1  GPIO47", "DIN1"),
            ("DIN2  GPIO16", "DIN2"),
            ("DIN3  GPIO14", "DIN3"),
            ("DIN4  GPIO13", "DIN4"),
        ],
        [("1-Wire  GPIO37", "OWGPIO")],
        [("SDA  GPIO4", "SDA"), ("SCL  GPIO5", "SCL")],
        [("pH RX  GPIO12", "EPH_RX"), ("pH TX  GPIO11", "EPH_TX")],
        [("ORP RX  GPIO40", "EOR_RX"), ("ORP TX  GPIO39", "EOR_TX")],
        [("GND", "GND")],
        [("BTN1  GPIO6", "BTN1"), ("BTN2  GPIO36", "BTN2")],
    ]
    right = []
    dy = 0.0
    key_dy = {}
    for index, group in enumerate(groups):
        if index:
            dy += GAP
        for name, key in group:
            right.append((name, dy))
            key_dy[key] = dy
            dy += PITCH
    sch.add_box("sensor-hat:Waveshare", "Waveshare", right, width=78.74)
    header = sch.place(
        "sensor-hat:Waveshare", "P1", "J1 + J2", 115, TOP, bom=False,
        extra={
            "ref_at": (70, TOP + 8),
            "val_at": (70, TOP + 4),
            "Description": "J1 is the USB-row socket. J2 is the relay-row socket. Both are on the back.",
        },
    )
    pin = {}
    for number, (name, _dy) in enumerate(right, start=1):
        key = name.split("  ")[0]
        # Keys are the second token stored above; recover from groups.
        pin[groups_key(groups, number)] = header[str(number)]

    sch.text("P1 is J1 and J2 together: the Pico sockets on the Waveshare.", 130, 12, 1.4)
    sch.text("J1 pins 4 and 5 are 3.3 V on the Waveshare. This hat does not connect them.", 130, 17, 1.2)
    sch.text("U1 and U2 are UART. U3 is I2C on SDA and SCL. PGND is not ground.", 130, 22, 1.2)

    def xy(key):
        return pin[key][0], pin[key][1]

    def pwr_off(point, net, dx, dy):
        x, y = snap(point[0] + dx), snap(point[1] + dy)
        sch.wire(point[0], point[1], x, y)
        sch.pwr += 1
        sch.place(f"power:{net}", f"#PWR{sch.pwr:03d}", net, x, y, bom=False)
        return x, y

    def flag_near(point, dx=7.62):
        end = (snap(point[0] + dx), snap(point[1]))
        sch.flag(end[0], end[1])
        sch.wire(point[0], point[1], end[0], end[1])

    def resistor(ref, value, x, y, rot=90):
        return sch.place("Device:R", ref, value, x, y, FP_R, extra=r_extra(value), rot=rot)

    def hang_down(ref, value, kind, x, y):
        """Pin 1 on (x, y), pin 2 below it."""
        if kind == "R":
            part = resistor(ref, value, x, y - 3.81, rot=180)
        else:
            part = sch.place(
                "Device:C", ref, value, x, y - 3.81, FP_C,
                extra={"LCSC": LCSC["100n"], "Voltage": "100V"}, rot=180,
            )
        return part

    def clamp_at(ref, x, y):
        pins = sch.place(
            "Diode:BAT54S", ref, "BAT54S", x, y - 5.08, FP_SOT,
            extra={"LCSC": LCSC["BAT54S"], "Description": "pin 1 GND, pin 2 V3OUT, pin 3 signal"},
        )
        pwr_off(pins["1"], "GND", 0, -5.08)
        pwr_off(pins["2"], "V3OUT", 0, -5.08)
        return pins

    def straight(src, dst):
        sch.wire(src[0], src[1], dst[0], dst[1])

    def jog(src, dst, lane):
        """Orthogonal path. The vertical sits at lane, off both pins."""
        lane = snap(lane)
        sch.wire(src[0], src[1], lane, src[1])
        sch.wire(lane, src[1], lane, dst[1])
        sch.wire(lane, dst[1], dst[0], dst[1])

    # Power. Only J1 pin 11 is wired. F1 then feeds every 3.3 V load.
    y3 = xy("3V3")[1]
    fuse = sch.place("Device:Polyfuse", "F1", "0.2A", 155, y3, FP_FUSE, rot=270, extra={
        "Description": "0.2 A hold polyfuse, Bourns MF-MSMF020 or equal, 1812",
    })
    straight(pin["3V3"], fuse["1"])
    cap = sch.place(
        "Device:C", "C3", "100nF", fuse["2"][0] + 10.16, y3, FP_C, rot=270,
        extra={"LCSC": LCSC["100n"], "Voltage": "100V"},
    )
    straight(fuse["2"], cap["1"])
    pwr_off(cap["2"], "GND", 5.08, 0)
    p3 = pwr_off(fuse["1"], "+3V3", -10.16, -7.62)
    flag_near(p3, -7.62)
    v3 = pwr_off(cap["1"], "V3OUT", 10.16, -7.62)
    flag_near(v3, 7.62)
    gnd = pwr_off(pin["GND"], "GND", 7.62, 0)
    flag_near(gnd)
    sch.text("F1 feeds every 3.3 V load. Header pins 4 and 5 stay open.", 220, y3 - 16, 1.1)

    # One horizontal row per input. The screw symbol uses the same spacing.
    def row_parts(header_pin, series_ref, series_val, cap_ref, diode_ref):
        series = resistor(series_ref, series_val, header_pin[0] + 63.5, header_pin[1])
        sch.wire(header_pin[0], header_pin[1], series["2"][0], series["2"][1])
        cap = hang_down(cap_ref, "100nF", "C", series["2"][0] - 12.7, series["2"][1])
        sch.wire(cap["1"][0], cap["1"][1], series["2"][0], series["2"][1])
        pwr_off(cap["2"], "GND", 0, -2.54)
        clamp_at(diode_ref, series["2"][0], series["2"][1])
        return series

    sch.text("4-20 mA on J8. Left to right is 1 to 4. 150 ohm to ground, then 1k into the ADC.", 130, xy("ADC1")[1] - 8, 1.2)
    adc_rows = {}
    for n, key in enumerate(("ADC1", "ADC2", "ADC3", "ADC4"), start=1):
        y = xy(key)[1]
        series = row_parts(pin[key], f"R{n + 4}", "1k", f"C{n + 3}", f"D{n}")
        shunt = hang_down(f"R{n}", "150", "R", series["1"][0] + 10.16, y)
        straight(series["1"], shunt["1"])
        pwr_off(shunt["2"], "GND", 0, -2.54)
        sch.label(f"SIG{n}", series["1"][0] + 2.54, y)
        adc_rows[n] = (shunt["1"][0], y)

    ch_pins = [("GND", -12.7)] + [(f"CH{n}", key_dy[f"ADC{n}"] - key_dy["ADC1"]) for n in range(1, 5)]
    sch.add_box("sensor-hat:MA", "4-20 mA", (), ch_pins, width=27.94)
    j7 = sch.place(
        "sensor-hat:MA", "J8", "4-20 mA", 400 + 27.94, xy("ADC1")[1], FP_MC.format(n=5),
        extra={"ref_at": (412, xy("ADC1")[1] + 16), "val_at": (412, xy("ADC1")[1] + 12)},
    )
    pwr_off(j7["1"], "GND", -7.62, 0)
    for n in range(1, 5):
        straight(adc_rows[n], j7[str(n + 1)])

    sch.text("Contacts on J7. Left to right: IN1, IN2, IN3, IN4.", 130, xy("DIN1")[1] - 8, 1.2)
    # Screw order is the GPIO order: IN1 GPIO47, IN2 GPIO16, IN3 GPIO14, IN4 GPIO13.
    contact_rows = (("DIN1", 1), ("DIN2", 2), ("DIN3", 3), ("DIN4", 4))
    in_rows = {}
    for key, n in contact_rows:
        y = xy(key)[1]
        series = row_parts(pin[key], f"R{8 + n}", "1k", f"C{7 + n}", f"D{4 + n}")
        pull = sch.place(
            "Device:R", f"R{12 + n}", "10k", series["1"][0] + 10.16, y + 3.81, FP_R,
            extra=r_extra("10k"),
        )
        straight(series["1"], pull["1"])
        pwr_off(pull["2"], "V3OUT", 0, 5.08)
        sch.label(f"IN{n}", series["1"][0] + 2.54, y)
        in_rows[n] = pull["1"]

    in_pins = [("GND", -12.7)] + [(f"IN{n}", key_dy[key] - key_dy["DIN1"]) for key, n in contact_rows]
    sch.add_box("sensor-hat:Contact", "Contacts", (), in_pins, width=27.94)
    j8 = sch.place(
        "sensor-hat:Contact", "J7", "Contacts", 400 + 27.94, xy("DIN1")[1], FP_MC.format(n=5),
        extra={"ref_at": (412, xy("DIN1")[1] + 16), "val_at": (412, xy("DIN1")[1] + 12)},
    )
    pwr_off(j8["1"], "GND", -7.62, 0)
    for n in range(1, 5):
        straight(in_rows[n], j8[str(n + 1)])

    # 1-Wire. The shunt block is drawn open so the three choices are readable.
    # Fit one of them, or none. J6 is the screw terminal.
    y_ow = xy("OWGPIO")[1]
    sch.text("1-Wire. Fit one shunt on JP6, or none.", 130, y_ow - 8, 1.2)
    r21 = resistor("R21", "100", 160, y_ow)
    straight(pin["OWGPIO"], r21["2"])
    sch.label("OW", r21["1"][0] + 5.08, y_ow)
    sch.add_box(
        "sensor-hat:OW", "1-Wire", (),
        [("3V3", -7.62, 1), ("DATA", 0, 2), ("GND", 7.62, 3)],
        width=20.32,
    )
    ow = sch.place(
        "sensor-hat:OW", "J6", "1-Wire", 340, y_ow, FP_MC.format(n=3),
        extra={
            "Pin order": "1 3V3, 2 DATA, 3 GND",
            "ref_at": (348, y_ow - 2),
            "val_at": (348, y_ow + 3),
        },
    )
    straight(r21["1"], ow["2"])
    pwr_off(ow["1"], "V3OUT", 0, -5.08)
    pwr_off(ow["3"], "GND", 0, 5.08)
    sch.add_box(
        "sensor-hat:JP6", "one shunt",
        [("OW", 0, 2), ("OW", 10.16, 4), ("OW", 20.32, 6)],
        [("4.7k", 0, 1), ("2.2k", 10.16, 3), ("1k", 20.32, 5)],
        width=22.86,
    )
    jp6 = sch.place(
        "sensor-hat:JP6", "JP6", "fit one", 250, y_ow - 7.62 - 20.32, FP_JUMP6,
        extra={"Description": "Fit ONE shunt: pins 1-2 are 4.7k, 3-4 are 2.2k, 5-6 are 1k"},
    )
    sch.wire(jp6["2"][0], jp6["2"][1], jp6["4"][0], jp6["4"][1])
    sch.wire(jp6["4"][0], jp6["4"][1], jp6["6"][0], jp6["6"][1])
    sch.wire(jp6["6"][0], jp6["6"][1], jp6["6"][0], y_ow)
    pulls = ((1, "R24", "4.7k"), (3, "R25", "2.2k"), (5, "R26", "1k"))
    pull_parts = []
    for odd, ref, value in pulls:
        pad = jp6[str(odd)]
        part = resistor(ref, value, pad[0] - 16, pad[1])
        straight(part["1"], pad)
        pull_parts.append(part)
    sch.wire(pull_parts[0]["2"][0], pull_parts[0]["2"][1], pull_parts[1]["2"][0], pull_parts[1]["2"][1])
    sch.wire(pull_parts[1]["2"][0], pull_parts[1]["2"][1], pull_parts[2]["2"][0], pull_parts[2]["2"][1])
    pwr_off(pull_parts[0]["2"], "V3OUT", -7.62, 0)

    def ezo_block(title, uref, data_ref, end_ref, probe_ref, rx_key, tx_key, r_rx, r_tx, prb, pgnd, link="series"):
        y_rx, y_tx = xy(rx_key)[1], xy(tx_key)[1]
        sock_w = 17.78
        if link == "series":
            sch.text(title + ". Plug in. Do not solder the board down.", 130, y_rx - 8, 1.2)
            rr = resistor(r_rx, "100", 165, y_rx)
            rt = resistor(r_tx, "100", 165, y_tx)
            straight(pin[rx_key], rr["2"])
            straight(pin[tx_key], rt["2"])
            rx_src, tx_src = rr["1"], rt["1"]
            data_pins = [("GND", -10.16, 1), ("RX", 0, 3), ("TX", y_tx - y_rx, 2)]
            pin_order = "1 GND, 2 TX, 3 RX"
            board_rx, board_tx = "RX", "TX"
        else:
            sch.text(
                title + ". Switch this module to I2C before you plug it in. Pull-ups are fitted. J16 is the same bus: pin 1 GND toward the USB edge, then 3.3 V, SCL, and SDA toward the screws.",
                130, y_rx - 8, 1.2,
            )
            # Pin 2 of each resistor sits on the signal wire. Pin 1 goes up to 3.3 V.
            rs = resistor(r_rx, "4.7k", snap(165), y_rx - 3.81, rot=0)
            rt = resistor(r_tx, "4.7k", snap(165), y_tx - 3.81, rot=0)
            sch.add_box(
                "sensor-hat:J16", "I2C",
                [("GND", -12.7, 1), ("3V3", -7.62, 2), ("SCL", y_rx - y_tx, 3), ("SDA", 0, 4)],
                width=15.24,
            )
            j6 = sch.place(
                "sensor-hat:J16", "J16", "I2C",
                snap(pin[tx_key][0] + 20.32), y_tx,
                "Connector_PinSocket_2.54mm:PinSocket_1x04_P2.54mm_Vertical",
                extra={"Pin order": "1 GND, 2 3V3, 3 SCL, 4 SDA. Pin 1 is on the left. Female socket, so the OLED plugs in."},
            )
            straight(pin[tx_key], j6["4"])
            straight(j6["4"], rt["2"])
            straight(pin[rx_key], j6["3"])
            straight(j6["3"], rs["2"])
            pwr_off(j6["1"], "GND", 0, -5.08)
            pwr_off(j6["2"], "V3OUT", -7.62, 0)
            pwr_off(rs["1"], "V3OUT", 0, -5.08)
            pwr_off(rt["1"], "V3OUT", 0, -5.08)
            rx_src, tx_src = rs["2"], rt["2"]
            data_pins = [("GND", -10.16, 1), ("SCL", 0, 3), ("SDA", y_tx - y_rx, 2)]
            pin_order = "1 GND, 2 SDA (TX pin), 3 SCL (RX pin)"
            board_rx, board_tx = "SCL", "SDA"
        sch.add_box(
            f"sensor-hat:{data_ref}", "data", (),
            data_pins,
            width=sock_w,
        )
        data = sch.place(
            f"sensor-hat:{data_ref}", data_ref, "data socket", rx_src[0] + sock_w + 15.24, y_rx,
            FP_EZO, extra={"Place on": "Top (F.Cu)", "Pin order": pin_order},
        )
        straight(rx_src, data["3"])
        straight(tx_src, data["2"])
        pwr_off(data["1"], "GND", 0, -5.08)
        board_w = 35.56
        sch.add_box(
            f"sensor-hat:{uref}", title,
            [("PGND", 0, 1), ("PRB", 7.62, 2), ("VCC", y_tx - y_rx, 3)],
            [("GND", -10.16, 4), (board_rx, 0, 5), (board_tx, y_tx - y_rx, 6)],
            width=board_w,
        )
        board = sch.place(
            f"sensor-hat:{uref}", uref, title, data["3"][0] + board_w + 12.7, y_rx,
            bom=False,
            extra={
                "ref_at": (data["3"][0] + 18, y_rx - 14),
                "val_at": (data["3"][0] + 32, y_rx - 14),
            },
        )
        straight(data["1"], board["4"])
        straight(data["3"], board["5"])
        straight(data["2"], board["6"])
        end_w = 16.51
        sch.add_box(
            f"sensor-hat:{end_ref}", "probe", (),
            [("VCC", y_tx - y_rx, 1), ("PRB", 7.62, 2), ("PGND", 0, 3)],
            width=end_w,
        )
        end = sch.place(
            f"sensor-hat:{end_ref}", end_ref, "probe socket", board["1"][0] + end_w + 12.7, y_rx,
            FP_EZO, extra={"Place on": "Top (F.Cu)", "Pin order": "1 VCC, 2 PRB, 3 PGND"},
        )
        straight(board["3"], end["1"])
        straight(board["2"], end["2"])
        straight(board["1"], end["3"])
        pwr_off(end["1"], "V3OUT", 0, 5.08)
        sch.add_box(
            f"sensor-hat:{probe_ref}", "wires", (),
            [("PRB", 7.62, 1), ("PGND", 0, 2)],
            width=15.24,
        )
        probe = sch.place(
            f"sensor-hat:{probe_ref}", probe_ref, title + " probe", end["2"][0] + 15.24 + 16, y_rx,
            FP_MC.format(n=2),
            extra={"Pin order": "1 PRB, 2 PGND. PGND is not digital ground."},
        )
        straight(end["2"], probe["1"])
        straight(end["3"], probe["2"])
        sch.label(prb, (end["2"][0] + probe["1"][0]) / 2, end["2"][1])
        sch.label(pgnd, (end["3"][0] + probe["2"][0]) / 2, end["3"][1])

    ezo_block(
        "EZO pH", "U1", "J11", "J12", "J3",
        "EPH_RX", "EPH_TX", "R17", "R18", "PH_PRB", "PH_PGND",
    )
    ezo_block(
        "EZO ORP", "U2", "J9", "J10", "J4",
        "EOR_RX", "EOR_TX", "R19", "R20", "ORP_PRB", "ORP_PGND",
    )
    ezo_block(
        "EZO I2C", "U3", "J13", "J14", "J5",
        "SCL", "SDA", "R28", "R27", "EZO_PRB", "EZO_PGND",
        link="pullup",
    )

    sch.text(
        "Buttons A and B sit at the USB-left corner. Each switch closes to ground. A 10k pulls the input up to the fused 3.3 V.",
        130, xy("BTN1")[1] - 8, 1.2,
    )

    def button(key, sw_ref, r_ref):
        src = pin[key]
        y = src[1]
        pull = resistor(r_ref, "10k", snap(src[0] + 20.32), y - 3.81, rot=0)
        straight(src, pull["2"])
        pwr_off(pull["1"], "V3OUT", 0, -5.08)
        sw = sch.place(
            "Switch:SW_Push", sw_ref, "TS-1187A",
            snap(pull["2"][0] + 25.4), y,
            "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
            rot=180,
            extra={"Description": "pin 1 to GND, pin 2 to the GPIO. Silk A is SW1, silk B is SW2."},
        )
        straight(pull["2"], sw["2"])
        pwr_off(sw["1"], "GND", 5.08, 0)

    button("BTN1", "SW1", "R29")
    button("BTN2", "SW2", "R30")
    return sch


def groups_key(groups, number):
    count = 0
    for group in groups:
        for _name, key in group:
            count += 1
            if count == number:
                return key
    raise SystemExit(f"no pin {number}")


def write_bom(parts, path):
    lines = ["Ref,Value,Footprint,LCSC"]
    for ref, value, footprint, lcsc in parts:
        lines.append(f"{ref},{value},{footprint},{lcsc}")
    path.write_text("\n".join(lines) + "\n")


def write_symbol_lib(sch):
    chunks = []
    for lib_id, block in sch.raw_syms.items():
        if not lib_id.startswith("sensor-hat:"):
            continue
        name = lib_id.split(":", 1)[1]
        block = block.replace(f'(symbol "{lib_id}"', f'(symbol "{name}"', 1)
        chunks.append("\n".join("\t" + line for line in block.splitlines()))
    (OUT / "sensor-hat.kicad_sym").write_text(
        "(kicad_symbol_lib\n"
        "\t(version 20251024)\n"
        '\t(generator "kicad_symbol_editor")\n'
        '\t(generator_version "10.0")\n'
        + "\n".join(chunks)
        + "\n)\n"
    )
    (OUT / "sym-lib-table").write_text(
        "(sym_lib_table\n"
        "\t(version 7)\n"
        '\t(lib (name "sensor-hat") (type "KiCad") '
        '(uri "${KIPRJMOD}/sensor-hat.kicad_sym") (options "") '
        '(descr "Waveshare interface and EZO blocks"))\n'
        ")\n"
    )


def main():
    sch = build()
    sch.emit(OUT / "sensor-hat.kicad_sch")
    write_symbol_lib(sch)
    write_bom(sch.bom, OUT / "bom.csv")
    print(f"parts {len(sch.bom)} wires {len(sch.wires)} labels {len(sch.labels)}")


if __name__ == "__main__":
    main()
