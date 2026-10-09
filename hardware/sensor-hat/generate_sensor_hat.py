#!/usr/bin/env python3
"""Generate the pool sensor hat KiCad board, schematic, BOM, and a placement preview.

Coordinates are millimetres, KiCad style: X to the right, Y up.
Mounted orientation: Y-up is the Waveshare USB side, X-right is the antenna side.
The female socket is on the bottom, against the top edge, right of center.
It is a Pico socket: two 1x20 rows, 2.54 mm along each row, 17.78 mm between rows.
A Raspberry Pi 40-pin GPIO header is 2.54 mm between rows and is not this footprint.
"""

import heapq
import math
import time
import uuid
from collections import defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent

BOARD_W = 132.0
BOARD_H = 70.0
# Pin 40 / pin 1 (antenna, 5 V end) pin-center.
RIGHT_X = 116.0
TOP_Y = 65.2
# Pico row spacing is 0.7 in. A Pi GPIO 2x20 header is one pitch, 2.54 mm.
ROW_GAP = 17.78
BOT_Y = TOP_Y - ROW_GAP
PITCH = 2.54

# Clearances and sizes.
SIG_W = 0.25
PWR_W = 0.50
GND_W = 0.40
VIA_OD = 0.80
VIA_DR = 0.40
PAD_HDR = 1.70
DRILL_HDR = 1.00
PAD_TERM = 2.40
DRILL_TERM = 1.40
CLEAR = 0.20


def uid():
    return str(uuid.uuid4())


def px(idx):
    """X of header column idx, 0 at the antenna end."""
    return RIGHT_X - idx * PITCH


def dist_point_seg(px_, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px_ - x1, py - y1)
    t = max(0.0, min(1.0, ((px_ - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px_ - (x1 + t * dx), py - (y1 + t * dy))


def _orient(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _on_seg(a, b, p):
    return (
        min(a[0], b[0]) - 1e-6 <= p[0] <= max(a[0], b[0]) + 1e-6
        and min(a[1], b[1]) - 1e-6 <= p[1] <= max(a[1], b[1]) + 1e-6
    )


def _segs_intersect(a, b, c, d):
    o1, o2 = _orient(a, b, c), _orient(a, b, d)
    o3, o4 = _orient(c, d, a), _orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    if abs(o1) < 1e-9 and _on_seg(a, b, c):
        return True
    if abs(o2) < 1e-9 and _on_seg(a, b, d):
        return True
    if abs(o3) < 1e-9 and _on_seg(c, d, a):
        return True
    if abs(o4) < 1e-9 and _on_seg(c, d, b):
        return True
    return False


def seg_seg_dist(a, b, c, d):
    # Non-crossing segments are closest at an endpoint.
    if _segs_intersect(a, b, c, d):
        return 0.0
    return min(
        dist_point_seg(a[0], a[1], c[0], c[1], d[0], d[1]),
        dist_point_seg(b[0], b[1], c[0], c[1], d[0], d[1]),
        dist_point_seg(c[0], c[1], a[0], a[1], b[0], b[1]),
        dist_point_seg(d[0], d[1], a[0], a[1], b[0], b[1]),
    )


class Board:
    def __init__(self):
        self.nets = {"": 0}
        self.pads = []  # dicts
        self.tracks = []
        self.vias = []
        self.graphics = []  # gr_line / gr_text / fp graphics stored as tuples
        self.footprints = []
        self.bom = []

    def net(self, name):
        if name not in self.nets:
            self.nets[name] = len(self.nets)
        return self.nets[name]

    def add_fp(self, ref, value, layer, at, pads, lines, texts):
        self.footprints.append(
            {
                "ref": ref,
                "value": value,
                "layer": layer,
                "at": at,
                "rot": 0,
                "pads": pads,
                "lines": lines,
                "texts": texts,
            }
        )
        for p in pads:
            rec = dict(p)
            rec["ref"] = ref
            if rec["net"]:
                self.net(rec["net"])
            self.pads.append(rec)

    def track(self, net, x1, y1, x2, y2, layer, width):
        if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6:
            return
        self.net(net)
        self.tracks.append(
            {"net": net, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "layer": layer, "w": width}
        )

    def ortho(self, net, pts, layer, width):
        """Route an orthogonal polyline. pts are (x, y). Inserts a corner if needed."""
        if len(pts) < 2:
            return
        seq = [pts[0]]
        for x, y in pts[1:]:
            px_, py = seq[-1]
            if abs(px_ - x) > 1e-6 and abs(py - y) > 1e-6:
                seq.append((x, py))
            seq.append((x, y))
        for (x1, y1), (x2, y2) in zip(seq, seq[1:]):
            self.track(net, x1, y1, x2, y2, layer, width)

    def via(self, net, x, y):
        self.net(net)
        self.vias.append({"net": net, "x": x, "y": y})

    def silk(self, text, x, y, layer="F.SilkS", size=1.0, rot=0):
        self.graphics.append(("text", text, x, y, layer, size, rot))

    def line(self, x1, y1, x2, y2, layer, width=0.12):
        self.graphics.append(("line", x1, y1, x2, y2, layer, width))

    def rect(self, x1, y1, x2, y2, layer, width=0.12):
        self.line(x1, y1, x2, y1, layer, width)
        self.line(x2, y1, x2, y2, layer, width)
        self.line(x2, y2, x1, y2, layer, width)
        self.line(x1, y2, x1, y1, layer, width)

    def check(self):
        problems = []
        # Track vs foreign pads.
        for t in self.tracks:
            hw = t["w"] / 2
            for p in self.pads:
                if p["net"] == t["net"]:
                    continue
                # Through-hole pads exist on both copper layers. SMD only on their layer.
                if p["th"] is False and p["layer"] != t["layer"]:
                    continue
                r = max(p["sx"], p["sy"]) / 2
                d = dist_point_seg(p["x"], p["y"], t["x1"], t["y1"], t["x2"], t["y2"])
                if d < r + hw + CLEAR - 1e-3:
                    problems.append(
                        f"track {t['net']} {t['x1']:.2f},{t['y1']:.2f}-{t['x2']:.2f},{t['y2']:.2f} "
                        f"{t['layer']} vs {p['ref']}.{p['num']} ({p['net']}) "
                        f"at {p['x']:.2f},{p['y']:.2f} gap {d - r - hw:.3f}"
                    )
        # Track vs track.
        for i, a in enumerate(self.tracks):
            for b in self.tracks[i + 1 :]:
                if a["net"] == b["net"] or a["layer"] != b["layer"]:
                    continue
                need = a["w"] / 2 + b["w"] / 2 + CLEAR
                d = seg_seg_dist(
                    (a["x1"], a["y1"]),
                    (a["x2"], a["y2"]),
                    (b["x1"], b["y1"]),
                    (b["x2"], b["y2"]),
                )
                if d < need - 1e-3:
                    problems.append(
                        f"tracks {a['net']} {a['x1']:.1f},{a['y1']:.1f}-{a['x2']:.1f},{a['y2']:.1f} / "
                        f"{b['net']} {b['x1']:.1f},{b['y1']:.1f}-{b['x2']:.1f},{b['y2']:.1f} "
                        f"on {a['layer']} gap {d - (a['w']+b['w'])/2:.3f}"
                    )
        # Via vs foreign pads.
        for v in self.vias:
            for p in self.pads:
                if p["net"] == v["net"]:
                    continue
                r = max(p["sx"], p["sy"]) / 2
                d = math.hypot(v["x"] - p["x"], v["y"] - p["y"])
                if d < r + VIA_OD / 2 + CLEAR - 1e-3:
                    problems.append(
                        f"via {v['net']} at {v['x']:.2f},{v['y']:.2f} vs pad {p['ref']}.{p['num']} "
                        f"gap {d - r - VIA_OD/2:.3f}"
                    )
        for i, a in enumerate(self.pads):
            ra = max(a["sx"], a["sy"]) / 2
            for p in self.pads[i + 1 :]:
                rb = max(p["sx"], p["sy"]) / 2
                d = math.hypot(a["x"] - p["x"], a["y"] - p["y"])
                need = ra + rb + (0.0 if a["net"] and a["net"] == p["net"] else CLEAR)
                if d < need - 1e-3 and d < ra + rb + 0.8:
                    problems.append(
                        f"pads {a['ref']}.{a['num']} ({a['net']}) / {p['ref']}.{p['num']} ({p['net']}) "
                        f"gap {d - ra - rb:.3f}"
                    )
        return problems


def th_pad(num, x, y, net, shape, size, drill):
    return {
        "num": str(num),
        "x": x,
        "y": y,
        "net": net,
        "shape": shape,
        "sx": size,
        "sy": size,
        "drill": drill,
        "th": True,
        "layer": "F.Cu",
    }


def smd_pad(num, x, y, net, sx, sy, layer="F.Cu"):
    return {
        "num": str(num),
        "x": x,
        "y": y,
        "net": net,
        "shape": "roundrect",
        "sx": sx,
        "sy": sy,
        "drill": None,
        "th": False,
        "layer": layer,
    }


def build():
    b = Board()
    N = b.net

    # ---------- header ----------
    # idx 0 is the antenna end. Top row is pins 40..21. Inner row is pins 1..20.
    header_nets = {}
    top_name = {
        0: ("5V", ""),
        1: ("VSYS", ""),
        2: ("GND", "GND"),
        3: ("3V3", "V3"),
        4: ("3V3", "V3"),
        5: ("GPIO10", ""),
        6: ("GPIO9", "EPH_RX"),  # ESP RX, from EZO TX
        7: ("GND", "GND"),
        8: ("GPIO8", "EPH_TX"),  # ESP TX, to EZO RX
        9: ("GPIO7", "ADC4"),
        10: ("3V3", "V3"),
        11: ("GPIO6", "ADC3"),
        12: ("GND", "GND"),
        13: ("GPIO5", "ADC2"),
        14: ("GPIO4", "ADC1"),
        15: ("GPIO40", "SCL"),
        16: ("GPIO39", "SDA"),
        17: ("GND", "GND"),
        18: ("GPIO3", ""),
        19: ("GPIO21", ""),
    }
    bot_name = {
        0: ("TXD", ""),
        1: ("RXD", ""),
        2: ("GND", "GND"),
        3: ("GPIO13", ""),
        4: ("GPIO14", "DIN1"),
        5: ("GPIO15", "DIN2"),
        6: ("GPIO16", ""),
        7: ("GND", "GND"),
        8: ("GPIO47", "DIN4"),
        9: ("GPIO48", ""),
        10: ("GPIO17", ""),
        11: ("GPIO18", ""),
        12: ("GND", "GND"),
        13: ("GPIO35", "DIN3"),
        14: ("GPIO36", ""),
        15: ("GPIO37", "OWGPIO"),
        16: ("GPIO38", ""),
        17: ("GND", "GND"),
        18: ("GPIO11", "EOR_RX"),
        19: ("GPIO12", "EOR_TX"),
    }
    hpads = []
    for idx in range(20):
        x = px(idx)
        pico_top = 40 - idx
        pico_bot = 1 + idx
        tn, tnet = top_name[idx]
        bn, bnet = bot_name[idx]
        hpads.append(
            th_pad(pico_top, x, TOP_Y, tnet, "rect" if pico_top == 40 else "circle", PAD_HDR, DRILL_HDR)
        )
        shape = "rect" if pico_bot == 1 else "circle"
        hpads.append(th_pad(pico_bot, x, BOT_Y, bnet, shape, PAD_HDR, DRILL_HDR))
        header_nets[pico_top] = (x, TOP_Y, tn, tnet)
        header_nets[pico_bot] = (x, BOT_Y, bn, bnet)
    b.add_fp("J1", "Pico_2x20_socket", "B.Cu", (0, 0), hpads, [], [])

    # Two separate 1x20 sockets, not one 2x20 Pi header.
    left_x = px(19)
    end_ext = 1.5
    body_half = 1.4
    for y in (TOP_Y, BOT_Y):
        b.rect(left_x - end_ext, y - body_half, RIGHT_X + end_ext, y + body_half, "B.SilkS", 0.15)
    dim_x = left_x - 3.0
    b.line(dim_x, TOP_Y, dim_x, BOT_Y, "F.SilkS", 0.15)
    b.line(dim_x - 1.4, TOP_Y, dim_x + 1.4, TOP_Y, "F.SilkS", 0.15)
    b.line(dim_x - 1.4, BOT_Y, dim_x + 1.4, BOT_Y, "F.SilkS", 0.15)
    b.silk("17.78 mm", dim_x - 8.0, (TOP_Y + BOT_Y) / 2, "F.SilkS", 1.6)
    b.silk("PIN 40  5V", RIGHT_X + 7.2, TOP_Y, "F.SilkS", 1.5)
    b.silk("PIN 1  TXD", RIGHT_X + 7.2, BOT_Y, "F.SilkS", 1.5)
    b.silk("ANTENNA END  ->", RIGHT_X - 18, TOP_Y + 2.8, "F.SilkS", 1.0)
    b.silk("USB SIDE OF WAVESHARE", BOARD_W / 2, BOARD_H - 1.3, "F.SilkS", 1.1)
    b.silk("TOWARD RELAYS", BOARD_W / 2, 1.3, "F.SilkS", 1.1)
    b.silk("Pool sensor hat  R1", 28, BOARD_H - 2.2, "F.SilkS", 1.4)

    # ---------- helpers to place parts ----------
    bom = b.bom

    def r0805(ref, value, x, y, net_a, net_b, vertical=True):
        if vertical:
            pads = [
                smd_pad(1, x, y + 0.85, net_a, 1.30, 0.95),
                smd_pad(2, x, y - 0.85, net_b, 1.30, 0.95),
            ]
        else:
            pads = [
                smd_pad(1, x - 0.85, y, net_a, 0.95, 1.30),
                smd_pad(2, x + 0.85, y, net_b, 0.95, 1.30),
            ]
        b.add_fp(ref, value, "F.Cu", (0, 0), pads, [], [])
        b.silk(ref, x + 1.6, y + 1.5, size=0.6)
        bom.append((ref, value, "0805", "resistor"))
        return pads

    def c0805(ref, value, x, y, net_a, net_b, vertical=True):
        if vertical:
            pads = [
                smd_pad(1, x, y + 0.85, net_a, 1.30, 0.95),
                smd_pad(2, x, y - 0.85, net_b, 1.30, 0.95),
            ]
        else:
            pads = [
                smd_pad(1, x - 0.85, y, net_a, 0.95, 1.30),
                smd_pad(2, x + 0.85, y, net_b, 0.95, 1.30),
            ]
        b.add_fp(ref, value, "F.Cu", (0, 0), pads, [], [])
        b.silk(ref, x + 1.6, y - 1.4, size=0.6)
        bom.append((ref, value, "0805", "capacitor"))
        return pads

    def sot23_bat54s(ref, x, y, net_gnd, net_v, net_sig):
        # Pin 1 anode to GND, pin 2 cathode to 3V3, pin 3 midpoint to signal.
        pads = [
            smd_pad(1, x - 1.05, y + 0.90, net_gnd, 0.90, 0.75),
            smd_pad(2, x + 1.05, y + 0.90, net_v, 0.90, 0.75),
            smd_pad(3, x, y - 1.00, net_sig, 0.90, 0.75),
        ]
        b.add_fp(ref, "BAT54S", "F.Cu", (0, 0), pads, [], [])
        b.silk(ref, x + 2.2, y, size=0.55)
        bom.append((ref, "BAT54S", "SOT-23", "series Schottky clamp, pin3 = signal"))
        return pads

    def sod123_zener(ref, x, y, net_sig, net_gnd):
        # Cathode (pin 1, band) up on SIG, anode down on GND.
        pads = [
            smd_pad(1, x, y + 1.35, net_sig, 1.10, 0.90),
            smd_pad(2, x, y - 1.35, net_gnd, 1.10, 0.90),
        ]
        b.add_fp(ref, "BZT52C5V1", "F.Cu", (0, 0), pads, [], [])
        b.silk(ref, x + 1.8, y, size=0.55)
        bom.append((ref, "BZT52C5V1", "SOD-123", "5.1 V zener"))
        return pads

    def ptc(ref, x, y, net_a, net_b):
        pads = [
            smd_pad(1, x - 2.0, y, net_a, 1.70, 2.20),
            smd_pad(2, x + 2.0, y, net_b, 1.70, 2.20),
        ]
        b.add_fp(ref, "0.2A", "F.Cu", (0, 0), pads, [], [])
        b.silk("F1 0.2A", x, y + 2.4, size=0.7)
        bom.append((ref, "polyfuse 0.2 A hold", "1812", "Bourns MF-MSMF020 or equal"))
        return pads

    def jumper_1x2(ref, x, y, net_a, net_b, label):
        pads = [
            th_pad(1, x, y, net_a, "rect", 1.70, 1.00),
            th_pad(2, x, y - 2.54, net_b, "circle", 1.70, 1.00),
        ]
        b.add_fp(ref, "JUMPER", "F.Cu", (0, 0), pads, [], [])
        b.silk(label, x + 2.2, y - 0.6, size=0.7)
        bom.append((ref, "1x2 pin header", "2.54 mm", "shunt jumper"))
        return pads

    def term(ref, value, pins, vertical, label):
        """pins: list of (local_index starting 1, abs x, abs y, net)."""
        pads = []
        for num, x, y, net in pins:
            shape = "rect" if num == 1 else "circle"
            pads.append(th_pad(num, x, y, net, shape, PAD_TERM, DRILL_TERM))
        b.add_fp(ref, value, "F.Cu", (0, 0), pads, [], [])
        xs = [p[1] for p in pins]
        ys = [p[2] for p in pins]
        if vertical:
            b.silk(label, min(xs) - 1.5, (max(ys) + min(ys)) / 2, size=0.9, rot=90)
        else:
            b.silk(label, (max(xs) + min(xs)) / 2, max(ys) + 3.2, size=0.9)
        # Pin-1 tick.
        b.silk("1", pins[0][1] - 1.8, pins[0][2] + 1.6, size=0.7)
        bom.append((ref, value, "3.50 mm pluggable", label))
        return pads

    # ---------- left-edge plugs, pin 1 at the top ----------
    def vpins(x, y_top, names):
        out = []
        for i, (name, net) in enumerate(names):
            out.append((i + 1, x, y_top - i * 3.50, net))
        return out

    # The two EZO plugs sit together on the left edge. Pin 1 is the top pin of each.
    eph = term(
        "J6",
        "1x04",
        vpins(16, 64, [("3V3", "V3OUT"), ("GND", "GND"), ("TX", "EPH_TXC"), ("RX", "EPH_RXC")]),
        True,
        "EZO pH",
    )
    eor = term(
        "J2",
        "1x04",
        vpins(16, 45.5, [("3V3", "V3OUT"), ("GND", "GND"), ("TX", "EOR_TXC"), ("RX", "EOR_RXC")]),
        True,
        "EZO ORP",
    )
    ow = term(
        "J3",
        "1x03",
        vpins(16, 29, [("3V3", "V3OUT"), ("DATA", "OW"), ("GND", "GND")]),
        True,
        "1-WIRE",
    )
    i2c = term(
        "J4",
        "1x04",
        vpins(16, 16, [("3V3", "V3OUT"), ("GND", "GND"), ("SDA", "SDAC"), ("SCL", "SCLC")]),
        True,
        "I2C",
    )

    # ---------- bottom plugs ----------
    def hpins(x_left, y, names):
        out = []
        for i, (name, net) in enumerate(names):
            out.append((i + 1, x_left + i * 3.50, y, net))
        return out

    c420 = term(
        "J5",
        "1x05",
        hpins(
            78,
            14,
            [("GND", "GND"), ("CH1", "SIG1"), ("CH2", "SIG2"), ("CH3", "SIG3"), ("CH4", "SIG4")],
        ),
        False,
        "4-20 mA",
    )
    din = term(
        "J7",
        "1x05",
        hpins(
            112,
            14,
            [("GND", "GND"), ("IN1", "IN1"), ("IN2", "IN2"), ("IN3", "IN3"), ("IN4", "IN4")],
        ),
        False,
        "CONTACT",
    )

    # ---------- 4-20 mA front ends, one column per channel ----------
    # Connector signal X is the column.
    chans = [
        (1, "SIG1", "SH1", "ADC1", 4),
        (2, "SIG2", "SH2", "ADC2", 5),
        (3, "SIG3", "SH3", "ADC3", 6),
        (4, "SIG4", "SH4", "ADC4", 7),
    ]
    # 6 mm pitch so a track fits beside the SOT-23 clamps.
    sig_x = {1: 74.0, 2: 80.0, 3: 86.0, 4: 92.0}
    for n, sig, sh, adc, _gpio in chans:
        x = sig_x[n]
        r0805(f"R{n}", "150", x, 44, sig, sh, vertical=True)
        jumper_1x2(f"JP{n}", x, 39.6, sh, "GND", "150")
        r0805(f"R{n+4}", "1k", x, 33, sig, adc, vertical=True)
        c0805(f"C{n+3}", "100n", x, 28, adc, "GND", vertical=True)
        sod123_zener(f"D{n+8}", x, 21.5, sig, "GND")
        sot23_bat54s(f"D{n}", x, 16.2, "GND", "V3", adc)
        b.silk(f"CH{n}", x, 47.2, size=0.8)

    # ---------- digital inputs ----------
    # Columns above the contact plug. IN3's GPIO is farther left; the net still ends here.
    din_x = {1: 108.0, 2: 114.0, 3: 120.0, 4: 126.0}
    for n in range(1, 5):
        x = din_x[n]
        r0805(f"R{12+n}", "10k", x, 40, "V3", f"IN{n}", vertical=True)  # R13-R16
        r0805(f"R{8+n}", "1k", x, 34, f"IN{n}", f"DIN{n}", vertical=True)  # R9-R12
        c0805(f"C{7+n}", "100n", x, 28.5, f"DIN{n}", "GND", vertical=True)  # C8-C11
        sot23_bat54s(f"D{4+n}", x, 22.5, "GND", "V3", f"DIN{n}")  # D5-D8
        b.silk(f"IN{n}", x, 43.2, size=0.7)

    # ---------- EZO series resistors ----------
    # pH connector nets EPH_TXC / EPH_RXC to header nets EPH_TX / EPH_RX.
    # Series resistors sit just to the right of the matching EZO plug.
    r0805("R17", "100", 22, 57, "EPH_TXC", "EPH_RX", vertical=False)  # EZO TX -> ESP RX
    r0805("R18", "100", 22, 53.5, "EPH_RXC", "EPH_TX", vertical=False)  # EZO RX -> ESP TX
    c0805("C12", "100n", 30, 61, "V3OUT", "GND", vertical=False)
    r0805("R19", "100", 22, 38.5, "EOR_TXC", "EOR_RX", vertical=False)
    r0805("R20", "100", 22, 35, "EOR_RXC", "EOR_TX", vertical=False)
    c0805("C13", "100n", 48, 56, "V3OUT", "GND", vertical=False)

    # ---------- 1-wire pull-up select ----------
    # 2x3: column 1 is the resistors, column 2 is DATA.
    jp_x, jp_y = 30.0, 40.0
    ow_pads = []
    pairs = [("4K7", "PU47"), ("2K2", "PU22"), ("1K0", "PU10")]
    for i, (label, net) in enumerate(pairs):
        y = jp_y - i * 2.54
        ow_pads.append(th_pad(1 + i * 2, jp_x, y, net, "rect" if i == 0 else "circle", 1.70, 1.00))
        ow_pads.append(th_pad(2 + i * 2, jp_x + 2.54, y, "OW", "circle", 1.70, 1.00))
        b.silk(label, jp_x - 3.4, y, size=0.6)
    b.add_fp("JP6", "1-wire pull-up", "F.Cu", (0, 0), ow_pads, [], [])
    bom.append(("JP6", "2x3 pin header", "2.54 mm", "fit ONE shunt: 4.7k, 2.2k, or 1k"))
    r0805("R24", "4.7k", 30, 46.5, "V3OUT", "PU47", vertical=False)
    r0805("R25", "2.2k", 38, 43.5, "V3OUT", "PU22", vertical=False)
    r0805("R26", "1k", 38, 36.5, "V3OUT", "PU10", vertical=False)
    r0805("R21", "100", 46, 40, "OW", "OWGPIO", vertical=False)
    b.silk("ONE JUMPER", 36, 32.2, size=0.6)

    # ---------- I2C pull-ups ----------
    jumper_1x2("JP5", 28, 26, "V3OUT", "I2CPU", "I2C PU")
    r0805("R27", "4.7k", 36, 26, "I2CPU", "SDAC", vertical=False)
    r0805("R28", "4.7k", 36, 22, "I2CPU", "SCLC", vertical=False)
    r0805("R22", "100", 48, 26, "SDAC", "SDA", vertical=False)
    r0805("R23", "100", 48, 22, "SCLC", "SCL", vertical=False)
    c0805("C14", "100n", 42, 18, "V3OUT", "GND", vertical=False)

    # ---------- power ----------
    ptc("F1", 58, 36, "V3", "V3OUT")
    c0805("C1", "10u", 46, 42, "V3", "GND", vertical=False)
    c0805("C2", "100n", 54, 42, "V3", "GND", vertical=False)
    c0805("C3", "100n", 66, 36, "V3OUT", "GND", vertical=False)
    b.silk("3V3", 58, 39.2, size=0.8)

    bom.append(("", "jumper shunt", "2.54 mm", "6 pieces: 4 shunts fitted, 1 on JP6, JP5 optional"))

    # ---------- routes ----------
    # Index lookup.
    def top_xy(pico):
        idx = 40 - pico
        return px(idx), TOP_Y

    def bot_xy(pico):
        idx = pico - 1
        return px(idx), BOT_Y

    def gap_left_of(idx):
        """X of the gap on the left side of this column (toward the far end)."""
        return px(idx + 0.5)

    def gap_right_of(idx):
        return px(idx - 0.5)

    # 3V3 bus above the header, then down a gap between the two 3V3 pins.
    bus_y = TOP_Y + 2.15
    b.ortho("V3", [(px(10), bus_y), (px(3), bus_y)], "F.Cu", PWR_W)
    for pico in (37, 36, 30):
        x, y = top_xy(pico)
        b.track("V3", x, y, x, bus_y, "F.Cu", PWR_W)
    escape_x = gap_left_of(3)  # between pin 37 and pin 36, both 3V3
    b.track("V3", escape_x, bus_y, escape_x, 56, "F.Cu", 0.40)
    b.track("V3", escape_x, 56, 52, 56, "F.Cu", PWR_W)  # into C1 / the PTC side

    # V3OUT trunk stays off the connector pin column. Stubs to each plug are added once
    # the connector pads exist.
    # Cross the left edge in the gap between the two EZO plugs (pin centers 53.5 and 45.5).
    b.track("V3OUT", 62, 49, 10, 49, "F.Cu", PWR_W)
    b.track("V3OUT", 10, 64, 10, 16, "F.Cu", PWR_W)

    # GND spine on the back, in that same gap, plus a lower spine between the
    # 1-wire plug and the I2C plug.
    gnd_y = 49.0
    low_gnd = 19.0
    b.track("GND", 12, gnd_y, 128, gnd_y, "B.Cu", 0.60)
    b.track("GND", 12, low_gnd, 128, low_gnd, "B.Cu", 0.50)
    b.track("GND", 12, gnd_y, 12, low_gnd, "B.Cu", 0.50)
    b.track("GND", 128, gnd_y, 128, low_gnd, "B.Cu", 0.50)
    for pico in (38, 33, 28, 23):
        x, y = top_xy(pico)
        b.track("GND", x, y, x, gnd_y, "B.Cu", GND_W)
    # Inner-row grounds are already on those same X lines (same net). Tie them too
    # so the ratsnest is obvious.
    for pico in (3, 8, 13, 18):
        x, y = bot_xy(pico)
        b.track("GND", x, BOT_Y, x, gnd_y, "B.Cu", GND_W)

    # Top-row signal escape. Each signal goes up into its own gap, then down to y=50.
    # (idx, gap function, net)
    escapes = [
        (6, "L", "EPH_RX"),
        (8, "R", "EPH_TX"),
        (9, "L", "ADC4"),
        (11, "R", "ADC3"),
        (13, "R", "ADC2"),
        (14, "L", "ADC1"),
        (15, "L", "SCL"),
        (16, "L", "SDA"),
    ]
    lane = TOP_Y + 1.15
    for idx, side, net in escapes:
        x = px(idx)
        gx = gap_left_of(idx) if side == "L" else gap_right_of(idx)
        pico = 40 - idx
        b.ortho(net, [(x, TOP_Y), (x, lane), (gx, lane), (gx, 50)], "F.Cu", SIG_W)

    # Inner-row signals drop straight to y=50, then run to their parts.
    # Pico pin, not GPIO number. Pin 5 is GPIO14.
    for pico, net in (
        (5, "DIN1"),
        (6, "DIN2"),
        (9, "DIN4"),
        (14, "DIN3"),
        (16, "OWGPIO"),
        (19, "EOR_RX"),
        (20, "EOR_TX"),
    ):
        x, y = bot_xy(pico)
        # Drop beside the pin, not through the pad below, then over to a lane.
        b.ortho(net, [(x, y), (x, y - 1.6), (x - 1.0, y - 1.6), (x - 1.0, 50)], "F.Cu", SIG_W)

    # Connect escaped nets from y=50 to the part pads. Pads are known by net and ref.
    def pads_of(ref, num=None, net=None):
        out = []
        for p in b.pads:
            if p["ref"] != ref:
                continue
            if num is not None and p["num"] != str(num):
                continue
            if net is not None and p["net"] != net:
                continue
            out.append(p)
        return out

    def p1(ref, num):
        hit = pads_of(ref, num)
        if not hit:
            raise SystemExit(f"missing {ref} pad {num}")
        return hit[0]["x"], hit[0]["y"]

    # ADC nets: from the gap drop (already at y=50) over to the top pad of R5-R8.
    for n, adc in ((1, "ADC1"), (2, "ADC2"), (3, "ADC3"), (4, "ADC4")):
        x, y = p1(f"R{n+4}", 1)  # top of 1k, ADC? Wait R{n+4} pin 1 is SIG side (top).
        # r0805 vertical: pad 1 is the upper pad = first net = sig, pad 2 = adc.
        x2, y2 = p1(f"R{n+4}", 2)
        # Step into the gap beside the column, then up. The column itself is full of parts.
        b.ortho(adc, [(x2, y2), (x2 + 1.55, y2), (x2 + 1.55, 50)], "F.Cu", SIG_W)

    # The escape verticals end at y=50 but at gap X, not resistor X. Bridge them.
    # Easier: for each escaped net, find track endpoints at y==50 and the pad, and connect.
    def endpoints(net, layer="F.Cu"):
        pts = []
        for t in b.tracks:
            if t["net"] == net and t["layer"] == layer:
                pts.append((t["x1"], t["y1"]))
                pts.append((t["x2"], t["y2"]))
        return pts

    def bridge_y(net, y, layer="F.Cu"):
        xs = [x for x, yy in endpoints(net, layer) if abs(yy - y) < 1e-3]
        # Also resistor/header pads already connected to a stub that reaches y.
        if len(xs) >= 2:
            b.track(net, min(xs), y, max(xs), y, layer, SIG_W)

    for adc in ("ADC1", "ADC2", "ADC3", "ADC4", "EPH_TX", "EPH_RX", "SCL", "SDA"):
        bridge_y(adc, 50)

    # SIG nets: connector pin up to 150R top (pad 1) and 1k top (pad 1 of R5-R8).
    for n in range(1, 5):
        sig = f"SIG{n}"
        cx, cy = p1("J5", n + 1)
        rx, ry = p1(f"R{n}", 1)
        sx, sy = p1(f"R{n+4}", 1)
        zx, zy = p1(f"D{n+8}", 1)
        b.ortho(sig, [(cx, cy), (cx, ry), (rx, ry)], "F.Cu", SIG_W)
        b.ortho(sig, [(rx, ry), (sx, sy)], "F.Cu", SIG_W)
        b.ortho(sig, [(sx, sy), (zx, zy)], "F.Cu", SIG_W)
        # Shunt bottom to jumper top.
        sh = f"SH{n}"
        a, b_ = p1(f"R{n}", 2), p1(f"JP{n}", 1)
        b.ortho(sh, [a, b_], "F.Cu", SIG_W)
        # Jumper bottom is GND (already a pad). Tie it down to the lower GND spine.
        gx, gy = p1(f"JP{n}", 2)
        b.track("GND", gx, gy, gx, low_gnd, "B.Cu", GND_W)

    # Clamp and cap grounds, and ADC node ties.
    for n in range(1, 5):
        adc = f"ADC{n}"
        # 1k bottom, cap top, diode pin 3
        pts = [p1(f"R{n+4}", 2), p1(f"C{n+3}", 1), p1(f"D{n}", 3)]
        # Bring them to the resistor x.
        for x, y in pts[1:]:
            b.ortho(adc, [pts[0], (x, y)], "F.Cu", SIG_W)
        # cap bottom and diode pin 1 to GND spine
        for ref, num in ((f"C{n+3}", 2), (f"D{n}", 1), (f"D{n+8}", 2)):
            x, y = p1(ref, num)
            b.via("GND", x + 1.1, y)
            b.track("GND", x, y, x + 1.1, y, "F.Cu", SIG_W)
            b.track("GND", x + 1.1, y, x + 1.1, low_gnd, "B.Cu", GND_W)
        # diode pin 2 is V3
        x, y = p1(f"D{n}", 2)
        b.ortho("V3", [(x, y), (x + 1.55, y), (x + 1.55, 56)], "F.Cu", SIG_W)

    # Digital columns to header nets.
    # DIN nets already drop to y=50 at the header X. Bridge to the 1k bottom? 
    # R9-R12: pin 1 is IN, pin 2 is DIN. Header is DIN.
    for n, header_net in ((1, "DIN1"), (2, "DIN2"), (3, "DIN3"), (4, "DIN4")):
        x, y = p1(f"R{8+n}", 2)
        b.ortho(header_net, [(x, y), (x + 1.55, y), (x + 1.55, 50)], "F.Cu", SIG_W)
        bridge_y(header_net, 50)
        # cap and clamp onto DIN
        for ref, num in ((f"C{7+n}", 1), (f"D{4+n}", 3)):
            px_, py = p1(ref, num)
            b.ortho(header_net, [(x, y), (px_, py)], "F.Cu", SIG_W)
        for ref, num in ((f"C{7+n}", 2), (f"D{4+n}", 1)):
            gx, gy = p1(ref, num)
            b.via("GND", gx + 1.1, gy)
            b.track("GND", gx, gy, gx + 1.1, gy, "F.Cu", SIG_W)
            b.track("GND", gx + 1.1, gy, gx + 1.1, low_gnd, "B.Cu", GND_W)
        vx, vy = p1(f"D{4+n}", 2)
        b.ortho("V3", [(vx, vy), (vx - 1.55, vy), (vx - 1.55, 56)], "F.Cu", SIG_W)
        # 10k from V3 to IN, and IN from connector
        in_net = f"IN{n}"
        topx, topy = p1(f"R{12+n}", 2)  # pad 2 is IN (lower pad of vertical 10k)
        # r0805(R13) net_a V3 upper, net_b IN lower. Yes pad 2 is IN.
        cx, cy = p1("J7", n + 1)
        b.ortho(in_net, [(topx, topy), (cx, cy)], "F.Cu", SIG_W)
        # 10k upper to V3 bus at y=56
        ux, uy = p1(f"R{12+n}", 1)
        b.track("V3", ux, uy, ux, 56, "F.Cu", SIG_W)

    # Connector grounds. Left-edge plugs share an X, so the drop steps
    # beside the pins instead of running through the other holes.
    for ref, nums in (("J2", (2,)), ("J3", (3,)), ("J4", (2,)), ("J5", (1,)), ("J6", (2,)), ("J7", (1,))):
        for num in nums:
            x, y = p1(ref, num)
            if x < 22:
                b.track("GND", x, y, 19, y, "B.Cu", GND_W)
                b.track("GND", 19, y, 19, low_gnd, "B.Cu", GND_W)
            else:
                b.track("GND", x, y, x, low_gnd, "B.Cu", GND_W)

    # EZO pH series resistors to header nets (already escaped to y=50).
    # Jog to the right of the pull-up header before dropping to the lane.
    b.ortho("EPH_RX", [p1("R17", 2), (38, 57), (38, 50)], "F.Cu", SIG_W)
    bridge_y("EPH_RX", 50)
    b.ortho("EPH_TX", [p1("R18", 2), (40, 53.5), (40, 50)], "F.Cu", SIG_W)
    bridge_y("EPH_TX", 50)
    # Connector side of those resistors.
    b.ortho("EPH_TXC", [p1("R17", 1), p1("J6", 3)], "F.Cu", SIG_W)
    b.ortho("EPH_RXC", [p1("R18", 1), p1("J6", 4)], "F.Cu", SIG_W)
    # Plug 3V3 pins. Short horizontal from the trunk into the hole.
    for ref in ("J6", "J2", "J3", "J4"):
        x, y = p1(ref, 1)
        b.track("V3OUT", 10, y, x, y, "F.Cu", PWR_W)

    # EZO ORP.
    b.ortho("EOR_TXC", [p1("R19", 1), p1("J2", 3)], "F.Cu", SIG_W)
    b.ortho("EOR_RXC", [p1("R20", 1), p1("J2", 4)], "F.Cu", SIG_W)
    x, y = p1("R19", 2)
    b.ortho("EOR_RX", [(x, y), (x, 45.2), (42, 45.2), (42, 50)], "F.Cu", SIG_W)
    bridge_y("EOR_RX", 50)
    x, y = p1("R20", 2)
    b.ortho("EOR_TX", [(x, y), (x, 32.2), (44, 32.2), (44, 50)], "F.Cu", SIG_W)
    bridge_y("EOR_TX", 50)
    # The three DATA pins of the pull-up header are the same net.
    b.track("OW", p1("JP6", 2)[0], p1("JP6", 2)[1], p1("JP6", 4)[0], p1("JP6", 4)[1], "F.Cu", SIG_W)
    b.track("OW", p1("JP6", 4)[0], p1("JP6", 4)[1], p1("JP6", 6)[0], p1("JP6", 6)[1], "F.Cu", SIG_W)
    b.ortho("OW", [p1("JP6", 2), p1("R21", 1)], "F.Cu", SIG_W)

    # 1-wire.
    b.ortho("OW", [p1("J3", 2), p1("R21", 1)], "F.Cu", SIG_W)
    x, y = p1("R21", 2)
    b.track("OWGPIO", x, y, x, 50, "F.Cu", SIG_W)
    bridge_y("OWGPIO", 50)
    # Pull-up resistors to the header and to V3OUT.
    b.ortho("PU47", [p1("R24", 2), p1("JP6", 1)], "F.Cu", SIG_W)
    b.ortho("PU22", [p1("R25", 2), p1("JP6", 3)], "F.Cu", SIG_W)
    b.ortho("PU10", [p1("R26", 2), p1("JP6", 5)], "F.Cu", SIG_W)
    for ref in ("R24", "R25", "R26"):
        x, y = p1(ref, 1)
        b.ortho("V3OUT", [(x, y), (10, 49)], "F.Cu", SIG_W)

    # I2C.
    b.ortho("SDAC", [p1("J4", 3), p1("R27", 2), p1("R22", 1)], "F.Cu", SIG_W)
    b.ortho("SCLC", [p1("J4", 4), p1("R28", 2), p1("R23", 1)], "F.Cu", SIG_W)
    for ref, num, net in (("R22", 2, "SDA"), ("R23", 2, "SCL")):
        x, y = p1(ref, num)
        b.track(net, x, y, x, 50, "F.Cu", SIG_W)
        bridge_y(net, 50)
    b.ortho("I2CPU", [p1("JP5", 2), p1("R27", 1), p1("R28", 1)], "F.Cu", SIG_W)
    b.ortho("V3OUT", [p1("JP5", 1), (10, 49)], "F.Cu", SIG_W)

    # Bulk caps to the rails.
    b.ortho("V3", [p1("C1", 1), p1("C2", 1), p1("F1", 1)], "F.Cu", PWR_W)
    b.ortho("V3OUT", [p1("F1", 2), p1("C3", 1)], "F.Cu", PWR_W)
    for ref, num in (("C1", 2), ("C2", 2), ("C3", 2), ("C12", 2), ("C13", 2), ("C14", 2)):
        x, y = p1(ref, num)
        b.via("GND", x, y - 1.3)
        b.track("GND", x, y, x, y - 1.3, "F.Cu", SIG_W)
        b.track("GND", x, y - 1.3, x, low_gnd if y - 1.3 > low_gnd else gnd_y, "B.Cu", GND_W)
    for ref in ("C12", "C13", "C14"):
        x, y = p1(ref, 1)
        b.ortho("V3OUT", [(x, y), (62, 49)], "F.Cu", SIG_W)

    # Tie V3 verticals that were sent up to y=56 into the 3V3 escape.
    b.track("V3", escape_x, 56, 40, 56, "F.Cu", 0.40)
    # Any V3 stub that reached y=56 gets joined.
    bridge_y("V3", 56)

    # Every installed connector hole gets a top-copper track that starts in the
    # hole and runs past the annular ring, so the joint is visible in KiCad.
    for p in b.pads:
        if p["ref"] not in ("J2", "J3", "J4", "J5", "J6", "J7") or not p["net"]:
            continue
        if p["x"] < 22:
            b.track(p["net"], p["x"], p["y"], p["x"] + 3.0, p["y"], "F.Cu", 0.50)
        else:
            # Leave the hole toward the board edge, clear of the parts above.
            b.track(p["net"], p["x"], p["y"], p["x"], p["y"] - 3.5, "F.Cu", 0.50)

    problems = b.check()
    return b, problems, header_nets


def _stroke(width):
    return f"(stroke (width {width:.2f}) (type solid))"


def emit_pcb(b, path):
    """Write a KiCad 9 board. KiCad 9 and 10 open this directly."""
    lines = []
    w = lines.append
    w("(kicad_pcb")
    w('  (version 20241229)')
    w('  (generator "pcbnew")')
    w('  (generator_version "9.0")')
    w("  (general")
    w("    (thickness 1.6)")
    w("    (legacy_teardrops no)")
    w("  )")
    w('  (paper "A3")')
    w("  (layers")
    for num, name, kind, *alias in (
        (0, "F.Cu", "signal"),
        (2, "B.Cu", "signal"),
        (9, "F.Adhes", "user", "F.Adhesive"),
        (11, "B.Adhes", "user", "B.Adhesive"),
        (13, "F.Paste", "user"),
        (15, "B.Paste", "user"),
        (5, "F.SilkS", "user", "F.Silkscreen"),
        (7, "B.SilkS", "user", "B.Silkscreen"),
        (1, "F.Mask", "user"),
        (3, "B.Mask", "user"),
        (17, "Dwgs.User", "user", "User.Drawings"),
        (19, "Cmts.User", "user", "User.Comments"),
        (21, "Eco1.User", "user", "User.Eco1"),
        (23, "Eco2.User", "user", "User.Eco2"),
        (25, "Edge.Cuts", "user"),
        (27, "Margin", "user"),
        (31, "F.CrtYd", "user", "F.Courtyard"),
        (29, "B.CrtYd", "user", "B.Courtyard"),
        (35, "F.Fab", "user"),
        (33, "B.Fab", "user"),
        (39, "User.1", "user"),
        (41, "User.2", "user"),
        (43, "User.3", "user"),
        (45, "User.4", "user"),
    ):
        if alias:
            w(f'    ({num} "{name}" {kind} "{alias[0]}")')
        else:
            w(f'    ({num} "{name}" {kind})')
    w("  )")
    w("  (setup")
    w("    (pad_to_mask_clearance 0)")
    w("    (allow_soldermask_bridges_in_footprints no)")
    w("    (tenting front back)")
    w("  )")
    for name, idx in b.nets.items():
        w(f'  (net {idx} "{name}")')

    def gr_line(x1, y1, x2, y2, layer, width):
        w("  (gr_line")
        w(f"    (start {x1:.3f} {y1:.3f})")
        w(f"    (end {x2:.3f} {y2:.3f})")
        w(f"    {_stroke(width)}")
        w(f'    (layer "{layer}")')
        w(f'    (uuid "{uid()}")')
        w("  )")

    for x1, y1, x2, y2 in (
        (0, 0, BOARD_W, 0),
        (BOARD_W, 0, BOARD_W, BOARD_H),
        (BOARD_W, BOARD_H, 0, BOARD_H),
        (0, BOARD_H, 0, 0),
    ):
        gr_line(x1, y1, x2, y2, "Edge.Cuts", 0.10)

    for g in b.graphics:
        if g[0] == "line":
            _, x1, y1, x2, y2, layer, width = g
            gr_line(x1, y1, x2, y2, layer, width)
        else:
            _, text, x, y, layer, size, rot = g
            esc = text.replace('"', "'")
            w("  (gr_text \"%s\"" % esc)
            w(f"    (at {x:.3f} {y:.3f} {rot})")
            w(f'    (layer "{layer}")')
            w(f'    (uuid "{uid()}")')
            w("    (effects")
            w("      (font")
            w(f"        (size {size:.2f} {size:.2f})")
            w("        (thickness 0.15)")
            w("      )")
            w("    )")
            w("  )")

    # Pads are stored in board coordinates. The footprint origin stays at 0,0.
    by_ref = {}
    for p in b.pads:
        by_ref.setdefault(p["ref"], []).append(p)
    fp_meta = {fp["ref"]: fp for fp in b.footprints}
    for ref, pads in by_ref.items():
        meta = fp_meta.get(ref, {})
        layer = meta.get("layer", "F.Cu")
        value = meta.get("value", ref)
        attr = "smd" if any(not p["th"] for p in pads) else "through_hole"
        w(f'  (footprint "PoolSensor:{ref}"')
        w(f'    (layer "{layer}")')
        w(f'    (uuid "{uid()}")')
        w("    (at 0 0)")
        w(f"    (attr {attr})")
        w('    (property "Reference" "%s"' % ref)
        w(f'      (at {pads[0]["x"]:.3f} {pads[0]["y"] + 2.2:.3f} 0)')
        w('      (layer "F.Fab")')
        w("      (hide yes)")
        w(f'      (uuid "{uid()}")')
        w("      (effects (font (size 0.6 0.6) (thickness 0.1)))")
        w("    )")
        w(f'    (property "Value" "{value}"')
        w(f'      (at {pads[0]["x"]:.3f} {pads[0]["y"] - 2.2:.3f} 0)')
        w('      (layer "F.Fab")')
        w("      (hide yes)")
        w(f'      (uuid "{uid()}")')
        w("      (effects (font (size 0.6 0.6) (thickness 0.1)))")
        w("    )")
        for p in pads:
            net_id = b.nets[p["net"]] if p["net"] else 0
            net_name = p["net"]
            w(f'    (pad "{p["num"]}" {"thru_hole" if p["th"] else "smd"} {p["shape"]}')
            w(f'      (at {p["x"]:.3f} {p["y"]:.3f})')
            w(f'      (size {p["sx"]:.2f} {p["sy"]:.2f})')
            if p["th"]:
                w(f'      (drill {p["drill"]:.2f})')
                # Name both copper layers. KiCad 10 draws a bare drill if it
                # does not accept the "*.Cu" wildcard on this footprint.
                w('      (layers "F.Cu" "B.Cu" "F.Mask" "B.Mask")')
            else:
                cu = p["layer"]
                w(f'      (layers "{cu}" "{cu.replace("Cu", "Mask")}" "{cu.replace("Cu", "Paste")}")')
                w("      (roundrect_rratio 0.15)")
            w(f'      (net {net_id} "{net_name}")')
            w(f'      (uuid "{uid()}")')
            w("    )")
        w("    (embedded_fonts no)")
        w("  )")

    for t in b.tracks:
        net_id = b.nets[t["net"]]
        w("  (segment")
        w(f'    (start {t["x1"]:.3f} {t["y1"]:.3f})')
        w(f'    (end {t["x2"]:.3f} {t["y2"]:.3f})')
        w(f'    (width {t["w"]:.2f})')
        w(f'    (layer "{t["layer"]}")')
        w(f"    (net {net_id})")
        w(f'    (uuid "{uid()}")')
        w("  )")
    for v in b.vias:
        net_id = b.nets[v["net"]]
        w("  (via")
        w(f'    (at {v["x"]:.3f} {v["y"]:.3f})')
        w(f"    (size {VIA_OD:.2f})")
        w(f"    (drill {VIA_DR:.2f})")
        w('    (layers "F.Cu" "B.Cu")')
        w(f"    (net {net_id})")
        w(f'    (uuid "{uid()}")')
        w("  )")

    # Unfilled ground zone. KiCad fills it with Edit > Fill All Zones.
    # The explicit GND tracks already join the ground pads.
    nid = b.nets["GND"]
    w("  (zone")
    w(f"    (net {nid})")
    w('    (net_name "GND")')
    w('    (layer "B.Cu")')
    w(f'    (uuid "{uid()}")')
    w("    (hatch edge 0.5)")
    w("    (connect_pads (clearance 0.30))")
    w("    (min_thickness 0.20)")
    w("    (filled_areas_thickness no)")
    w("    (fill")
    w("      (mode polygon)")
    w("      (thermal_gap 0.30)")
    w("      (thermal_bridge_width 0.40)")
    w("    )")
    w("    (polygon")
    w("      (pts")
    for x, y in ((1, 1), (BOARD_W - 1, 1), (BOARD_W - 1, BOARD_H - 1), (1, BOARD_H - 1)):
        w(f"        (xy {x:.2f} {y:.2f})")
    w("      )")
    w("    )")
    w("  )")
    w("  (embedded_fonts no)")
    w(")")
    path.write_text("\n".join(lines) + "\n")


def emit_sch(path):
    path.write_text(
        f"""(kicad_sch
  (version 20250114)
  (generator "eeschema")
  (generator_version "9.0")
  (uuid "{uid()}")
  (paper "A3")
  (title_block
    (title "Pool sensor hat")
    (rev "R1")
    (comment 1 "Pico socket for the Waveshare ESP32-S3-RELAY-6CH")
    (comment 2 "Two 1x20 rows, 2.54 mm pitch, 17.78 mm between rows")
    (comment 3 "Layout is on the PCB. This sheet is the project cover.")
  )
  (lib_symbols)
  (sheet_instances
    (path "/"
      (page "1")
    )
  )
  (embedded_fonts no)
)
"""
    )


def emit_svg(b, path):
    # Image Y down, board top (USB side) at the top of the picture.
    scale = 8
    m = 36

    def X(x):
        return m + x * scale

    def Y(y):
        return m + (BOARD_H - y) * scale

    w = int(BOARD_W * scale + 2 * m)
    h = int(BOARD_H * scale + 2 * m)
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        '<rect width="100%" height="100%" fill="#1e1e1e"/>',
        f'<rect x="{X(0)}" y="{Y(BOARD_H)}" width="{BOARD_W*scale}" height="{BOARD_H*scale}" '
        f'fill="#14301c" stroke="#d0d0d0" stroke-width="2"/>',
        '<g font-family="sans-serif" fill="#f2f2f2">',
        f'<text x="{m}" y="22" font-size="15">Top view. USB side up, antenna to the right. Pico socket on the back: two 1x20 rows, 2.54 mm along a row, 17.78 mm between rows.</text>',
    ]
    for g in b.graphics:
        if g[0] != "line" or g[5] not in ("F.SilkS", "B.SilkS"):
            continue
        _, x1, y1, x2, y2, layer, width = g
        stroke = "#8ec8e8" if layer == "B.SilkS" else "#f4f4f4"
        o.append(
            f'<line x1="{X(x1)}" y1="{Y(y1)}" x2="{X(x2)}" y2="{Y(y2)}" '
            f'stroke="{stroke}" stroke-width="{max(1, width*scale)}" fill="none"/>'
        )
    for p in b.pads:
        col = "#f0f0f0" if p["th"] else "#e8d48b"
        if p["net"] == "GND":
            col = "#8fd0a0"
        elif p["net"] in ("V3", "V3OUT"):
            col = "#e07070"
        o.append(
            f'<rect x="{X(p["x"])-p["sx"]/2*scale}" y="{Y(p["y"])-p["sy"]/2*scale}" '
            f'width="{p["sx"]*scale}" height="{p["sy"]*scale}" fill="{col}" stroke="#222" stroke-width="0.4"/>'
        )
        if p["th"] and p["drill"]:
            o.append(
                f'<circle cx="{X(p["x"])}" cy="{Y(p["y"])}" r="{p["drill"]/2*scale}" fill="#1e1e1e"/>'
            )
    # Copper after the pads so a trace that leaves a hole stays visible.
    for t in b.tracks:
        if t["layer"] != "B.Cu":
            continue
        o.append(
            f'<line x1="{X(t["x1"])}" y1="{Y(t["y1"])}" x2="{X(t["x2"])}" y2="{Y(t["y2"])}" '
            f'stroke="#3d7ea6" stroke-width="{max(1, t["w"]*scale)}" stroke-linecap="round"/>'
        )
    for t in b.tracks:
        if t["layer"] != "F.Cu":
            continue
        o.append(
            f'<line x1="{X(t["x1"])}" y1="{Y(t["y1"])}" x2="{X(t["x2"])}" y2="{Y(t["y2"])}" '
            f'stroke="#e0b040" stroke-width="{max(1, t["w"]*scale)}" stroke-linecap="round"/>'
        )
    for v in b.vias:
        o.append(
            f'<circle cx="{X(v["x"])}" cy="{Y(v["y"])}" r="{VIA_OD/2*scale}" fill="#888"/>'
        )
    for g in b.graphics:
        if g[0] != "text" or g[4] != "F.SilkS":
            continue
        _, text, x, y, layer, size, rot = g
        o.append(
            f'<text x="{X(x)}" y="{Y(y)}" font-size="{size*scale}" fill="#f4f4f4" '
            f'text-anchor="middle">{text}</text>'
        )
    o.append("</g></svg>")
    path.write_text("\n".join(o))


def emit_bom(b, path):
    lines = ["Ref,Value,Package,Notes"]
    for ref, value, pkg, notes in b.bom:
        lines.append(f'{ref},{value},{pkg},"{notes}"')
    path.write_text("\n".join(lines) + "\n")


def emit_pro(path):
    path.write_text(
        """{
  "board": {
    "design_settings": {
      "defaults": { "board_outline_line_width": 0.1 },
      "rules": { "min_clearance": 0.2 }
    }
  },
  "meta": { "filename": "sensor-hat.kicad_pro", "version": 1 },
  "net_settings": {
    "classes": [
      { "name": "Default", "clearance": 0.2, "track_width": 0.25, "via_dia": 0.8, "via_drill": 0.4 }
    ]
  },
  "pcbnew": { "page_layout_descr_file": "" },
  "schematic": { "legacy_lib_dir": "", "legacy_lib_list": [] },
  "sheets": [],
  "text_variables": {}
}
"""
    )


def main():
    raise SystemExit(
        "The schematic is build_schematic.py. This generator draws the old layout and is retired."
    )
    b, problems, _ = build()
    # Last contact pad must be inside the outline. Enforced by BOARD_W.
    emit_pcb(b, OUT / "sensor-hat.kicad_pcb")
    emit_sch(OUT / "sensor-hat.kicad_sch")
    emit_svg(b, OUT / "preview-top.svg")
    emit_bom(b, OUT / "bom.csv")
    emit_pro(OUT / "sensor-hat.kicad_pro")
    for t in b.tracks:
        if t["net"] == "DIN1":
            print("DIN1", round(t["x1"],2), round(t["y1"],2), round(t["x2"],2), round(t["y2"],2), t["layer"])
    for p in b.pads:
        if p["ref"] == "J1" and p["num"] in ("14", "5"):
            print("pad", p["num"], p["net"], round(p["x"],2), round(p["y"],2))
    from collections import Counter
    c = Counter(p.split(" vs ")[0] if " vs " in p else p for p in problems)
    print("problem groups", len(c))
    print(f"pads {len(b.pads)} tracks {len(b.tracks)} vias {len(b.vias)} nets {len(b.nets)}")
    print(f"clearance problems: {len(problems)}")
    for p in problems[:40]:
        print(" ", p)
    if len(problems) > 40:
        print(f"  ... {len(problems)-40} more")


if __name__ == "__main__":
    main()
