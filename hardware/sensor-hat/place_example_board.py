#!/usr/bin/env python3
"""Example board: outline, Pico sockets, screw terminals, and EZO sockets.

The 1-Wire, 4-20 mA, pH, ORP, I2C EZO, and contact circuits are placed and routed.
The back is a ground plane. Header ground pins are already common on the
Waveshare board, so the plane is the only ground wiring.
Header 3.3 V pins are common there too. Each load uses the nearest pin.
Three EZO circuits plug into female 1x3 sockets on the top. pH and ORP are
UART. The third is I2C on SDA and SCL, with 4.7k pull-ups fitted.
J16 is that same bus, a female 1x4 to the right of the third EZO board.
Pin 1 is GND toward the USB edge. Then 3.3 V, SCL, and SDA toward the screws.
The display sits far enough right to clear the Atlas boards. Two push
buttons at the USB-left corner are GPIO inputs for that display.
Parts may sit under those boards. Each probe screw is only the two probe wires.
EZO1, EZO2, and EZO3 are visual models of the Atlas boards for the 3D viewer.
They have no pads and they are not part of the hat.
"""

import pcbnew

OUT = "/home/mdahlgre/src/Pool-Controller/hardware/sensor-hat/sensor-hat.kicad_pcb"
SOCK_LIB = "/usr/share/kicad/footprints/Connector_PinSocket_2.54mm.pretty"
SOCK_NAME = "PinSocket_1x20_P2.54mm_Vertical"
EZO_NAME = "PinSocket_1x03_P2.54mm_Vertical"
PLUG_LIB = "/usr/share/kicad/footprints/TerminalBlock_Phoenix.pretty"
HDR_LIB = "/usr/share/kicad/footprints/Connector_PinHeader_2.54mm.pretty"
SOT_LIB = "/usr/share/kicad/footprints/Package_TO_SOT_SMD.pretty"
FUSE_LIB = "/usr/share/kicad/footprints/Fuse.pretty"
R_LIB = "/home/mdahlgre/.local/share/kicad/10.0/3rdparty/footprints/JLCPCB.pretty"

# +X is the antenna. 120 x 49 mm. The extra millimetre is the screw edge,
# so each terminal has a silk name past the housings. The J3/J4 gap was closed to 1 mm and
# two millimetres were removed from each side of the 124 mm outline, so
# J1 pin 15 (GPIO4) stays on the center line. The USB-row sockets are on the back,
# 3.5 mm from their edge.
BOARD_W = 120.0
BOARD_H = 49.0
ROW_GAP = 17.78
PITCH = 2.54
IO4_INDEX = 15  # J1 pin 15 is Pico pin 26, GPIO4
IO4_X = BOARD_W / 2
PIN1_X = round(IO4_X + (IO4_INDEX - 1) * PITCH, 2)
USB_ROW_Y = 3.5
RELAY_ROW_Y = round(USB_ROW_Y + ROW_GAP, 2)
# Screw-edge lane for the clamp feeds only. It starts at the 1-Wire
# terminal, not at the left edge. 0.25 mm track, 0.5 mm copper-to-edge.
V3_EDGE_Y = 47.30

# Pin 1 is the antenna end. 4-20 channels 2 to 4 use USB pins 9, 7, and 6.
# Channel 1 uses relay pin 4. Contacts use relay pins 9, 7, 6, and 5.
# pH UART is relay pins 20 and 19. ORP receive is USB pin 17 (GPIO39) and
# ORP transmit is USB pin 16 (GPIO40). I2C is USB pins 15 and 14. Button A
# is USB pin 10 (GPIO7). Button B is USB pin 12 (GPIO6). Relay pin 15 is
# open. Pin 20 on the USB row is the buzzer, so it stays open. Pin 11 is
# the fuse input.
USB_NETS = [
    None, None, "GND", "+3V3", "+3V3", "ADC4", "ADC3", "GND", "ADC2", "BTN1",
    "+3V3", "BTN2", "GND", "SCL", "SDA", "EOR_TX", "EOR_RX", "GND", None, None,
]
RELAY_NETS = [
    None, None, "GND", "ADC1", "DIN4", "DIN3", "DIN2", "GND", "DIN1", None,
    None, None, "GND", None, None, "OWGPIO", None, "GND", "EPH_TX", "EPH_RX",
]


def mm(value):
    return pcbnew.VECTOR2I_MM(value, 0).x and pcbnew.FromMM(value)


def vec(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


def load_fp(folder, name):
    fp = pcbnew.FootprintLoad(folder, name)
    if fp is None:
        raise SystemExit(f"missing footprint {name}")
    return fp


def ensure_net(board, names, net_name):
    if net_name not in names:
        item = pcbnew.NETINFO_ITEM(board, net_name)
        board.Add(item)
        names[net_name] = item
    return names[net_name]


def assign(board, names, fp, nets):
    for index, net_name in enumerate(nets, start=1):
        if not net_name:
            continue
        pad = fp.FindPadByNumber(str(index))
        pad.SetNet(ensure_net(board, names, net_name))


def socket(board, names, ref, y, nets):
    fp = load_fp(SOCK_LIB, SOCK_NAME)
    fp.SetReference(ref)
    fp.SetValue("1x20 socket, bottom")
    fp.SetPosition(vec(PIN1_X, y))
    # 270 degrees puts pin 1 at this point and pin 20 to the left.
    fp.SetOrientationDegrees(270)
    board.Add(fp)
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    assign(board, names, fp, nets)
    ref_text = fp.Reference()
    ref_text.SetLayer(pcbnew.F_SilkS)
    ref_text.SetMirrored(False)
    ref_text.SetTextAngleDegrees(0)
    ref_text.SetPosition(vec(PIN1_X + 4.5, y))
    ref_text.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    ref_text.SetTextThickness(mm(0.15))
    value = fp.Value()
    value.SetVisible(False)
    return fp


def ezo_socket(board, names, ref, x, y, nets):
    """One row of the EZO footprint. Pin 1 is at (x, y). Pins increase to the right."""
    fp = load_fp(SOCK_LIB, EZO_NAME)
    fp.SetReference(ref)
    fp.SetValue("EZO socket, top")
    fp.SetPosition(vec(x, y))
    fp.SetOrientationDegrees(90)
    board.Add(fp)
    assign(board, names, fp, nets)
    ref_text = fp.Reference()
    ref_text.SetLayer(pcbnew.F_SilkS)
    ref_text.SetMirrored(False)
    ref_text.SetTextAngleDegrees(0)
    ref_text.SetTextSize(pcbnew.VECTOR2I(mm(0.7), mm(0.7)))
    ref_text.SetTextThickness(mm(0.12))
    ref_text.SetPosition(vec(x + 7.4, y))
    fp.Value().SetVisible(False)
    return fp


def ezo_pair(board, names, data_ref, probe_ref, x, y, tx_net, rx_net, prb_net, pgnd_net):
    # Atlas footprint: GND TX RX, and 17.78 mm away, VCC PRB PGND.
    ezo_socket(board, names, data_ref, x, y, ["GND", tx_net, rx_net])
    ezo_socket(board, names, probe_ref, x, y + 17.78, ["V3OUT", prb_net, pgnd_net])


def plug(board, names, ref, value, x, y, pins, nets, ref_at):
    name = f"TerminalBlock_Phoenix_MKDS-1,5-{pins}-5.08_1x0{pins}_P5.08mm_Horizontal"
    fp = load_fp(PLUG_LIB, name)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(vec(x, y))
    # Pin 1 on the left, pins to the right. Wire opening faces the bottom edge.
    fp.SetOrientationDegrees(0)
    board.Add(fp)
    assign(board, names, fp, nets)
    ref_text = fp.Reference()
    ref_text.SetLayer(pcbnew.F_SilkS)
    ref_text.SetMirrored(False)
    ref_text.SetTextAngleDegrees(0)
    ref_text.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    ref_text.SetTextThickness(mm(0.12))
    ref_text.SetPosition(vec(*ref_at))
    ref_text.SetVisible(True)
    fp.Value().SetVisible(False)
    return fp


def segment(board, x1, y1, x2, y2, layer):
    shape = pcbnew.PCB_SHAPE(board)
    shape.SetShape(pcbnew.SHAPE_T_SEGMENT)
    shape.SetLayer(layer)
    shape.SetStart(vec(x1, y1))
    shape.SetEnd(vec(x2, y2))
    shape.SetWidth(mm(0.12))
    board.Add(shape)


def rect(board, x1, y1, x2, y2, layer, width=0.12):
    segment(board, x1, y1, x2, y1, layer)
    segment(board, x2, y1, x2, y2, layer)
    segment(board, x2, y2, x1, y2, layer)
    segment(board, x1, y2, x1, y1, layer)


def style_text(text, x, y, size):
    text.SetLayer(pcbnew.F_SilkS)
    text.SetMirrored(False)
    text.SetTextAngleDegrees(0)
    text.SetVisible(True)
    text.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    text.SetTextThickness(mm(0.12))
    text.SetPosition(vec(x, y))


def add_part(board, names, folder, fname, ref, value, x, y, rot, nets, lib_id):
    fp = load_fp(folder, fname)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(vec(x, y))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    fp.SetFPID(pcbnew.LIB_ID(lib_id[0], lib_id[1]))
    assign(board, names, fp, nets)
    return fp


def pad_xy(fp, number):
    pad = fp.FindPadByNumber(str(number))
    pos = pad.GetPosition()
    return pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)


def route(board, net, points, width, layer=None):
    if layer is None:
        layer = pcbnew.F_Cu
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if abs(x1 - x2) < 0.001 and abs(y1 - y2) < 0.001:
            continue
        track = pcbnew.PCB_TRACK(board)
        track.SetStart(vec(x1, y1))
        track.SetEnd(vec(x2, y2))
        track.SetWidth(mm(width))
        track.SetLayer(layer)
        track.SetNet(net)
        board.Add(track)


def onewire(board, names):
    """Dallas 1-Wire: series 100 ohm, and one of three pull-ups via JP6.

    F1 sits between the header rows, input on the pin 11 column. C3 is on
    the fused output. JP6 is centered in the slot between the third Atlas
    board and the display, just below the relay pins so the shunt can be
    reached with both boards installed. The pull-ups sit under that Atlas
    board. 3.3 V leaves the rail, runs under the display, and returns
    under the shunt. The data wire into J6 crosses that return, so that
    short span is on the back.
    """
    parts = {}
    # Rotation 180 puts the 3.3 V input on pin 11 and the output to its left.
    # The body is between the rows, clear of both courtyards.
    parts["F1"] = add_part(
        board, names, FUSE_LIB, "Fuse_1812_4532Metric",
        "F1", "0.2A", 66.0, 9.945, -90, ["+3V3", "V3OUT"],
        ("Fuse", "Fuse_1812_4532Metric"),
    )
    parts["C3"] = add_part(
        board, names, R_LIB, "C_0805",
        "C3", "100nF", 62.0, 10.895, 90, ["V3OUT", "GND"],
        ("PCM_JLCPCB", "C_0805"),
    )
    # Odd pins are the pull-ups. Even pins are the data net. Pin 1 is the
    # header end, on the Atlas side. The body is centered in the 8.2 mm
    # slot. The relay-row pads block anything higher.
    jp_y = 24.40
    pull_x = 45.40
    jp_x = 50.46
    parts["JP6"] = add_part(
        board, names, HDR_LIB, "PinHeader_2x03_P2.54mm_Vertical",
        "JP6", "one shunt", jp_x, jp_y, 0,
        ["PU47", "OW", "PU22", "OW", "PU10", "OW"],
        ("Connector_PinHeader_2.54mm", "PinHeader_2x03_P2.54mm_Vertical"),
    )
    pullups = (("R24", "4.7k", "PU47", 0), ("R25", "2.2k", "PU22", 1), ("R26", "1k", "PU10", 2))
    for ref, value, net, row in pullups:
        parts[ref] = add_part(
            board, names, R_LIB, "R_0805",
            ref, value, pull_x, jp_y + row * PITCH, 0, ["V3OUT", net],
            ("PCM_JLCPCB", "R_0805"),
        )
    # Right of the data column. Pad 1 faces the jumper, pad 2 the GPIO pin.
    parts["R21"] = add_part(
        board, names, R_LIB, "R_0805",
        "R21", "100", 55.50, 34.00, 90, ["OW", "OWGPIO"],
        ("PCM_JLCPCB", "R_0805"),
    )

    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    j1, j5 = fps["J1"], fps["J6"]
    # Pin 11 is the 3.3 V pin nearest the fuse. The other 3.3 V pins stay open.
    v3_hdr = pad_xy(j1, 11)
    ow_gpio = pad_xy(fps["J2"], 16)
    conn_v = pad_xy(j5, 1)
    conn_ow = pad_xy(j5, 2)

    f_in, f_out = pad_xy(parts["F1"], 1), pad_xy(parts["F1"], 2)
    c_v, c_g = pad_xy(parts["C3"], 1), pad_xy(parts["C3"], 2)
    r21_ow, r21_gpio = pad_xy(parts["R21"], 1), pad_xy(parts["R21"], 2)

    v3 = ensure_net(board, names, "V3OUT")
    gnd = ensure_net(board, names, "GND")
    p3 = ensure_net(board, names, "+3V3")
    ow = ensure_net(board, names, "OW")
    owgpio = ensure_net(board, names, "OWGPIO")

    # Straight drop from pin 11 into the fuse. The other 3.3 V pins stay open.
    route(board, p3, [v3_hdr, f_in], 0.3)
    gnd_via(board, gnd, c_g[0], c_g[1])
    # Between relay pins 18 and 19, then along the probe-socket row into
    # J14 pin 1. C3, R28, and R27 sit on the run that leaves the fuse.
    # The right-hand loads leave this drop below the 1-Wire resistor.
    j2 = fps["J2"]
    drop_x = round((pad_xy(j2, 18)[0] + pad_xy(j2, 19)[0]) / 2, 2)
    j14_v = pad_xy(fps["J14"], 1)
    socket_y = 24.2
    # The trunk steps between J16's SCL and SDA pads and stops at the drop.
    # Carrying it further left shorts SCL on the third EZO socket.
    route(board, v3, [
        f_out, (59.4, f_out[1]), (59.4, 14.43), (55.4, 14.43), (55.4, f_out[1]), (drop_x, f_out[1]),
    ], 0.30)
    route(board, v3, [(drop_x, 13.93), (51.0, 13.82)], 0.25)
    # Leave the rail before the display header, drop under the display
    # between relay pins 14 and 15, then come back under the shunt.
    v_pads = [pad_xy(parts[ref], 1) for ref, *_ in pullups]
    route(board, v3, [(55.20, 14.29), (55.20, 17.80), (61.27, 17.80), (61.27, 31.00)], 0.25)
    route(board, v3, [(61.27, 31.00), (57.35, 31.00)], 0.25)
    via(board, 57.35, 31.00, v3)
    route(board, v3, [(57.35, 31.00), (55.85, 31.00)], 0.25, pcbnew.B_Cu)
    via(board, 55.85, 31.00, v3)
    route(board, v3, [(55.85, 31.00), (v_pads[0][0], 31.00), v_pads[2], v_pads[0]], 0.25)
    route(board, v3, [(v_pads[0][0], socket_y), (j14_v[0], socket_y)], 0.25)
    j7_tap = pad_xy(fps["J8"], 5)[0] - 2.60
    route(board, v3, [(conn_v[0], 31.00), conn_v, (conn_v[0], V3_EDGE_Y), (j7_tap, V3_EDGE_Y)], 0.25)
    for ref, _value, net, row in pullups:
        src = pad_xy(parts[ref], 2)
        dst = pad_xy(parts["JP6"], 1 + 2 * row)
        route(board, ensure_net(board, names, net), [src, dst], 0.2)

    ow_pins = [pad_xy(parts["JP6"], n) for n in (2, 4, 6)]
    route(board, ow, ow_pins, 0.25)
    # Straight down on J6 pin 2. The 3.3 V return hops this vertical.
    route(board, ow, [ow_pins[2], (conn_ow[0], ow_pins[2][1]), conn_ow], 0.25)
    route(board, ow, [ow_pins[0], r21_ow], 0.2)
    route(board, owgpio, [r21_gpio, ow_gpio], 0.2)

    style_text(parts["F1"].Reference(), 68.02, 16.55, 0.55)
    style_text(parts["F1"].Value(), 68.02, 17.25, 0.5)
    style_text(parts["C3"].Reference(), 63.6, 16.9, 0.45)
    style_text(parts["C3"].Value(), 63.6, 17.6, 0.4)
    parts["JP6"].Value().SetVisible(False)
    style_text(parts["JP6"].Reference(), 51.9, 15.8, 0.55)
    fps["J6"].Reference().SetPosition(vec(56.63, 46.15))
    parts["R21"].Value().SetVisible(False)
    style_text(parts["R21"].Reference(), 57.4, 27.3, 0.45)
    # Shunt values sit to the right of the header, in the gap by the display.
    label_x = 56.0
    label_ys = (24.5, 27.0, 29.5)
    label_text = ("4.7k", "2.2k", "1.0k")
    for ref, value, _net, row in pullups:
        y = jp_y + row * PITCH
        parts[ref].Value().SetVisible(False)
        style_text(parts[ref].Reference(), 43.1, y, 0.4)
        item = silk(board, label_text[row], label_x, label_ys[row], 1.50, 0.18)
        item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        item.SetPosition(vec(label_x, label_ys[row]))


def via(board, x, y, net):
    item = pcbnew.PCB_VIA(board)
    item.SetPosition(vec(x, y))
    item.SetWidth(mm(0.6))
    item.SetDrill(mm(0.3))
    item.SetViaType(pcbnew.VIATYPE_THROUGH)
    item.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    item.SetNet(net)
    board.Add(item)
    return item


def gnd_via(board, gnd, x, y, dx=0, dy=0):
    """Via in the ground pad. The back plane finishes the connection."""
    via(board, x, y, gnd)


def ground_plane(board, names):
    """Solid ground on the back, inset from the board edge."""
    gnd = ensure_net(board, names, "GND")
    zone = pcbnew.ZONE(board)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetNet(gnd)
    zone.SetIsRuleArea(False)
    zone.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(mm(0.25))
    zone.SetThermalReliefSpokeWidth(mm(0.30))
    zone.SetMinThickness(mm(0.25))
    zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    zone.SetLocalClearance(mm(0.20))
    outline = pcbnew.SHAPE_POLY_SET()
    outline.NewOutline()
    margin = 0.5
    for x, y in (
        (margin, margin),
        (BOARD_W - margin, margin),
        (BOARD_W - margin, BOARD_H - margin),
        (margin, BOARD_H - margin),
    ):
        outline.Append(vec(x, y))
    # Keep the outline object alive. The zone holds it, and dropping the
    # Python wrapper before save has crashed pcbnew.
    board._zone_outline = outline
    zone.SetOutline(outline)
    zone.SetNeedRefill(True)
    board.Add(zone)


def ma420(board, names):
    """Four 4-20 mA inputs on the right, on J8.

    150 ohm always runs from the signal screw to ground. 1k, 100 nF, and a
    BAT54S clamp sit on the ADC side. Ground vias drop into the back plane.
    3.3 V is V3OUT, from the fuse drop. Channel 1 is a short front run to
    relay pin 4. Channels 2 to 4 stay on the front, between the header rows.
    """
    j7 = next(fp for fp in board.GetFootprints() if fp.GetReference() == "J8")
    sig_x = [pad_xy(j7, n)[0] for n in range(2, 6)]
    # Channel 1 is relay pin 4. Channels 2 to 4 are USB pins 9, 7, and 6.
    adc_pin = [None, 9, 7, 6]
    lane_y = [18.4, 16.8, 15.2, 13.6]
    parts = {}
    for n, sx in enumerate(sig_x, start=1):
        parts[f"R{n}"] = add_part(
            board, names, R_LIB, "R_0805",
            f"R{n}", "150", sx, 34.5, 0, [f"SIG{n}", "GND"],
            ("PCM_JLCPCB", "R_0805"),
        )
        parts[f"R{n+4}"] = add_part(
            board, names, R_LIB, "R_0805",
            f"R{n+4}", "1k", sx, 31.8, 0, [f"SIG{n}", f"ADC{n}"],
            ("PCM_JLCPCB", "R_0805"),
        )
        parts[f"C{n+3}"] = add_part(
            board, names, R_LIB, "C_0805",
            f"C{n+3}", "100nF", sx, 29.2, 180, [f"ADC{n}", "GND"],
            ("PCM_JLCPCB", "C_0805"),
        )
        parts[f"D{n}"] = add_part(
            board, names, SOT_LIB, "SOT-23",
            f"D{n}", "BAT54S", sx, 25.9, 0, ["GND", "V3OUT", f"ADC{n}"],
            ("Package_TO_SOT_SMD", "SOT-23"),
        )

    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    j1, j2, j7 = fps["J1"], fps["J2"], fps["J8"]
    gnd = ensure_net(board, names, "GND")
    v3 = ensure_net(board, names, "V3OUT")
    taps = []
    for n, sx in enumerate(sig_x, start=1):
        r_g = pad_xy(parts[f"R{n}"], 2)
        cap_g = pad_xy(parts[f"C{n+3}"], 2)
        clamp_g = pad_xy(parts[f"D{n}"], 1)
        gnd_via(board, gnd, r_g[0], r_g[1])
        gnd_via(board, gnd, cap_g[0], cap_g[1])
        gnd_via(board, gnd, clamp_g[0], clamp_g[1])
        taps.append((sx - 2.60, pad_xy(parts[f"D{n}"], 2)))
    # Up from the screw-edge lane, beside the screw, on the front.
    for tap, clamp in taps:
        route(board, v3, [(tap, V3_EDGE_Y), (tap, clamp[1]), clamp], 0.25)

    # Channels 2 to 4 leave the clamp, cut onto a lane, and rise into the
    # USB pin. Channel 1 ignores the first cut and runs straight to J2 pin 4.
    # rise_y, lane join x, lane end x, height of the last cut.
    adc_cuts = (
        (22.0, 98.7, 84.5, 6.6),
        (21.68, 102.5, 85.5, 6.54),
        (21.66, 106.0, 89.0, 6.5),
        (21.64, 109.5, 90.0, 6.5),
    )
    for n, sx, pin, lane, cut in zip(range(1, 5), sig_x, adc_pin, lane_y, adc_cuts):
        sig = ensure_net(board, names, f"SIG{n}")
        adc = ensure_net(board, names, f"ADC{n}")
        r_sig = pad_xy(parts[f"R{n}"], 1)
        conn = pad_xy(j7, n + 1)
        series_sig, series_adc = pad_xy(parts[f"R{n+4}"], 1), pad_xy(parts[f"R{n+4}"], 2)
        cap_a = pad_xy(parts[f"C{n+3}"], 1)
        clamp_a = pad_xy(parts[f"D{n}"], 3)
        rise_y, join_x, end_x, pin_y = cut

        route(board, sig, [conn, (r_sig[0], conn[1]), r_sig, series_sig], 0.25)
        route(board, adc, [series_adc, (series_adc[0], clamp_a[1]), clamp_a], 0.2)
        route(board, adc, [cap_a, (series_adc[0], cap_a[1])], 0.2)
        if n == 1:
            hdr = pad_xy(j2, 4)
            route(board, adc, [clamp_a, (clamp_a[0], 22.7), (hdr[0], 22.7), hdr], 0.2)
        else:
            adc_pad = pad_xy(j1, pin)
            route(board, adc, [
                clamp_a, (clamp_a[0], rise_y), (join_x, lane), (end_x, lane),
                (adc_pad[0], pin_y), adc_pad,
            ], 0.2)

        style_text(parts[f"R{n}"].Reference(), sx - 2.2, 34.1, 0.35)
        style_text(parts[f"R{n}"].Value(), sx + 2.2, 34.1, 0.35)
        style_text(parts[f"R{n+4}"].Reference(), sx - 2.2, 31.4, 0.35)
        style_text(parts[f"C{n+3}"].Reference(), sx - 2.2, 28.8, 0.35)
        style_text(parts[f"D{n}"].Reference(), sx + 2.15, 25.4, 0.35)

    j7.Reference().SetPosition(vec(106.45, 46.15))


def ezo(board, names):
    """pH and ORP UART, power, and probe wires.

    Series resistors sit under the EZO boards. Power is
    V3OUT after the fuse. Probe screws are PRB and PGND only. Both UARTs
    stay on the front.
    """
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    j1, j2 = fps["J1"], fps["J2"]
    # ORP receive is the upper lane, transmit the lower, so they do not cross.
    # pH stays lower and ends on the relay row.
    placed = {
        "R20": (43.59, 10.5, ["EZO_ORP_RX", "EOR_TX"]),
        "R19": (39.09, 8.5, ["EZO_ORP_TX", "EOR_RX"]),
        "R18": (16.065, 19.55, ["EZO_PH_RX", "EPH_TX"]),
        "R17": (27.74, 21.50, ["EZO_PH_TX", "EPH_RX"]),
    }
    parts = {}
    for ref, (x, y, nets) in placed.items():
        parts[ref] = add_part(
            board, names, R_LIB, "R_0805", ref, "100", x, y, 0, nets,
            ("PCM_JLCPCB", "R_0805"),
        )
        style_text(parts[ref].Reference(), x, y - 1.35, 0.4)
        style_text(parts[ref].Value(), x, y + 1.35, 0.4)
    v3 = ensure_net(board, names, "V3OUT")

    def wire(net_name, points):
        route(board, ensure_net(board, names, net_name), points, 0.25)

    # Same-x pairs drop straight. The others jog in the gap above the terminals.
    lane = 35.3

    def jog(net_name, src, dst):
        if abs(src[0] - dst[0]) < 0.05:
            wire(net_name, [src, dst])
        else:
            wire(net_name, [src, (src[0], lane), (dst[0], lane), dst])

    jog("PH_PGND", pad_xy(fps["J12"], 3), pad_xy(fps["J3"], 2))
    jog("PH_PRB", pad_xy(fps["J12"], 2), pad_xy(fps["J3"], 1))
    jog("ORP_PGND", pad_xy(fps["J10"], 3), pad_xy(fps["J4"], 2))
    jog("ORP_PRB", pad_xy(fps["J10"], 2), pad_xy(fps["J4"], 1))
    jog("EZO_PGND", pad_xy(fps["J14"], 3), pad_xy(fps["J5"], 2))
    jog("EZO_PRB", pad_xy(fps["J14"], 2), pad_xy(fps["J5"], 1))

    # Probe power is one run just above the sockets. J14 pin 1 is fed
    # straight from the fuse; pH and ORP tie onto that same run.
    bus_y = 24.2
    v_pads = [pad_xy(fps[ref], 1) for ref in ("J12", "J10", "J14")]
    route(board, v3, [(v_pads[0][0], bus_y), (v_pads[-1][0], bus_y)], 0.25)
    route(board, v3, [(4.80, bus_y), (6.38, bus_y)], 0.25)
    for pad in v_pads:
        route(board, v3, [(pad[0], bus_y), pad], 0.25)

    # Socket grounds are through-hole and meet the back plane.
    # pH transmit runs at the resistor, then across into relay pin 20.
    # pH receive is the short link into R18, then a lane under the sockets.
    r17_in, r17_out = pad_xy(parts["R17"], 1), pad_xy(parts["R17"], 2)
    r18_in, r18_out = pad_xy(parts["R18"], 1), pad_xy(parts["R18"], 2)
    ph_tx, ph_rx = pad_xy(fps["J11"], 2), pad_xy(fps["J11"], 3)
    pin_rx, pin_tx = pad_xy(j2, 20), pad_xy(j2, 19)
    route(board, parts["R17"].FindPadByNumber("1").GetNet(), [ph_tx, (ph_tx[0], r17_in[1]), r17_in], 0.2)
    route(board, parts["R17"].FindPadByNumber("2").GetNet(), [r17_out, (r17_out[0], 21.6), (pin_rx[0], 21.6), pin_rx], 0.2)
    route(board, parts["R18"].FindPadByNumber("1").GetNet(), [ph_rx, r18_in], 0.2)
    route(
        board,
        parts["R18"].FindPadByNumber("2").GetNet(),
        [r18_out, (r18_out[0], 17.9), (42.0, 17.9), (42.0, 18.6), (pin_tx[0], 18.6), pin_tx],
        0.2,
    )

    # Receive on the upper lane, transmit on the lower. Each end is a
    # short diagonal so the run does not travel the whole pin column.
    rx_src = pad_xy(fps["J9"], 2)
    rx_left, rx_right = pad_xy(parts["R19"], 1), pad_xy(parts["R19"], 2)
    rx_dst = pad_xy(j1, 17)
    rx_net_in = parts["R19"].FindPadByNumber("1").GetNet()
    rx_net = parts["R19"].FindPadByNumber("2").GetNet()
    route(board, rx_net_in, [rx_src, (rx_src[0], rx_left[1]), rx_left], 0.2)
    # Along y=2, then down into pin 17. Pin 16 stays to the right for transmit.
    route(board, rx_net, [rx_right, (38.0, 2.0), (rx_dst[0], 2.0), rx_dst], 0.2)

    tx_src = pad_xy(fps["J9"], 3)
    tx_left, tx_right = pad_xy(parts["R20"], 1), pad_xy(parts["R20"], 2)
    tx_dst = pad_xy(j1, 16)
    tx_net_in = parts["R20"].FindPadByNumber("1").GetNet()
    tx_net = parts["R20"].FindPadByNumber("2").GetNet()
    route(board, tx_net_in, [tx_src, (tx_src[0], tx_left[1]), tx_left], 0.2)
    route(board, tx_net, [tx_right, (56.25, tx_right[1]), (56.25, 2.0), (tx_dst[0], 2.0), tx_dst], 0.2)


def i2c(board, names):
    """Third EZO on SDA and SCL, plus a socket on that bus for an SSD1309.

    J16 stands to the right of the third EZO board so the display clears
    all three Atlas modules by about 4 mm. Pin 1 is ground, toward the
    USB edge. Pins step toward the screws: GND, 3.3 V, SCL, SDA. The
    glass stops above the screw terminals. About 10 mm hangs off the USB
    edge, and about 6.5 mm hangs off the antenna edge.
    """
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    j1 = fps["J1"]
    sda_pin, scl_pin = pad_xy(j1, 15), pad_xy(j1, 14)
    # Pin 1 toward the USB edge. Pins step toward the screws.
    header_x, header_y = 58.5, 9.5
    j6 = add_part(
        board, names, SOCK_LIB, "PinSocket_1x04_P2.54mm_Vertical",
        "J16", "Socket", header_x, header_y, 0, ["GND", "V3OUT", "SCL", "SDA"],
        ("Connector_PinSocket_2.54mm", "PinSocket_1x04_P2.54mm_Vertical"),
    )
    j6.Value().SetVisible(False)
    style_text(j6.Reference(), 51.8, 6.5, 0.45)
    for text, y in (("GND", 9.500), ("3V3", 11.945), ("SCL", 14.945), ("SDA", 17.120)):
        silk(board, text, 56.0, y, 0.45, 0.1)
    sock_sda = pad_xy(fps["J13"], 2)
    sock_scl = pad_xy(fps["J13"], 3)

    # R27 sits in the gap between the ORP board and the third socket.
    # R28 stands on the fused trunk.
    r27 = add_part(
        board, names, R_LIB, "R_0805", "R27", "4.7k", 32.65, 15.41, 90,
        ["V3OUT", "SDA"], ("PCM_JLCPCB", "R_0805"),
    )
    r28 = add_part(
        board, names, R_LIB, "R_0805", "R28", "4.7k", 51.0, 15.38, 90,
        ["V3OUT", "SCL"], ("PCM_JLCPCB", "R_0805"),
    )
    style_text(r27.Reference(), 34.6, 10.5, 0.4)
    style_text(r27.Value(), 34.6, 13.1, 0.4)
    style_text(r28.Reference(), 51.0, 11.0, 0.4)
    style_text(r28.Value(), 49.6, 12.46, 0.4)

    v3 = ensure_net(board, names, "V3OUT")
    sda = ensure_net(board, names, "SDA")
    scl = ensure_net(board, names, "SCL")
    gnd = ensure_net(board, names, "GND")
    scl_lane = pad_xy(r28, 2)[1]
    sda_pad = pad_xy(r27, 2)
    j6_gnd, j6_v = pad_xy(j6, 1), pad_xy(j6, 2)
    j6_scl, j6_sda = pad_xy(j6, 3), pad_xy(j6, 4)

    # SCL stays on the front and steps down the left side of the header.
    # SDA to the Pico header stays on the front. The run into J16 crosses
    # the fused drop on a short back segment.
    route(board, sda, [sock_sda, (sock_sda[0], 7.5)], 0.2)
    route(board, sda, [sda_pad, (sda_pad[0], 7.5), (55.0, 7.5), (55.0, 4.8), (sda_pin[0], 4.8), sda_pin], 0.2)
    route(board, sda, [(sock_sda[0], 11.0), (50.2, 11.0)], 0.2)
    via(board, 50.2, 11.0, sda)
    route(board, sda, [(50.2, 11.0), (55.4, 11.0), (55.4, j6_sda[1])], 0.2, pcbnew.B_Cu)
    via(board, 55.4, j6_sda[1], sda)
    route(board, sda, [(55.4, j6_sda[1]), j6_sda], 0.2)
    route(board, scl, [scl_pin, (scl_pin[0], 6.6), (55.6, 6.6), (55.6, scl_lane), pad_xy(r28, 2)], 0.2)
    route(board, scl, [(55.6, scl_lane), (55.6, j6_scl[1]), j6_scl], 0.2)
    route(board, scl, [pad_xy(r28, 2), (46.2, scl_lane), (46.2, sock_scl[1]), sock_scl], 0.2)

    gnd_via(board, gnd, *j6_gnd)
    # Display 3.3 V rises on the right of the header. SCL stays on the left.
    route(board, v3, [(58.4, 14.43), (58.4, j6_v[1]), j6_v], 0.30)
    # The rise into R27 hops the button trace on the back.
    r27_v = pad_xy(r27, 1)
    route(board, v3, [(r27_v[0], 24.2), (r27_v[0], 22.4)], 0.30)
    via(board, r27_v[0], 22.4, v3)
    route(board, v3, [(r27_v[0], 22.4), (r27_v[0], 13.5)], 0.30, pcbnew.B_Cu)
    via(board, r27_v[0], 13.5, v3)
    route(board, v3, [(r27_v[0], 13.5), r27_v], 0.30)


def contacts(board, names):
    """Dry contacts on J7. 10k to 3.3 V, 1k, 100 nF, and a clamp.

    3.3 V is V3OUT from the fuse drop. Ground vias drop into the
    back plane. D5 goes to relay pin 9, D6 to pin 7, D7 to pin 6, D8 to pin 5.
    """
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    j2, j8 = fps["J2"], fps["J7"]
    columns = [pad_xy(j8, n)[0] for n in range(2, 6)]
    # Left to right on the screws. D5 (IN1) is pin 9, D6 (IN2) is pin 7,
    # D7 (IN3) is pin 6, D8 (IN4) is pin 5.
    header_pins = [9, 7, 6, 5]
    parts = {}
    for n, sx in enumerate(columns, start=1):
        din_name = f"DIN{n}"
        parts[f"R{12+n}"] = add_part(
            board, names, R_LIB, "R_0805", f"R{12+n}", "10k", sx, 34.85, 0,
            ["V3OUT", f"IN{n}"], ("PCM_JLCPCB", "R_0805"),
        )
        parts[f"R{8+n}"] = add_part(
            board, names, R_LIB, "R_0805", f"R{8+n}", "1k", sx, 32.05, 0,
            [f"IN{n}", din_name], ("PCM_JLCPCB", "R_0805"),
        )
        parts[f"C{7+n}"] = add_part(
            board, names, R_LIB, "C_0805", f"C{7+n}", "100nF", sx, 29.90, 180,
            [din_name, "GND"], ("PCM_JLCPCB", "C_0805"),
        )
        parts[f"D{4+n}"] = add_part(
            board, names, SOT_LIB, "SOT-23", f"D{4+n}", "BAT54S", sx, 26.90, 0,
            ["GND", "V3OUT", din_name], ("Package_TO_SOT_SMD", "SOT-23"),
        )
        style_text(parts[f"R{12+n}"].Reference(), sx - 2.2, 34.5, 0.35)
        style_text(parts[f"R{8+n}"].Reference(), sx - 2.2, 31.7, 0.35)
        style_text(parts[f"C{7+n}"].Reference(), sx - 2.2, 29.55, 0.35)
        style_text(parts[f"D{4+n}"].Reference(), sx + 2.15, 26.4, 0.35)
    j8.Reference().SetPosition(vec(79.0, 46.15))

    gnd = ensure_net(board, names, "GND")
    v3 = ensure_net(board, names, "V3OUT")
    taps = []
    for n, sx, pin in zip(range(1, 5), columns, header_pins):
        inn = ensure_net(board, names, f"IN{n}")
        din = ensure_net(board, names, f"DIN{n}")
        rpu_3, rpu_in = pad_xy(parts[f"R{12+n}"], 1), pad_xy(parts[f"R{12+n}"], 2)
        rser_in, rser_din = pad_xy(parts[f"R{8+n}"], 1), pad_xy(parts[f"R{8+n}"], 2)
        cap_din, cap_g = pad_xy(parts[f"C{7+n}"], 1), pad_xy(parts[f"C{7+n}"], 2)
        dio_g, dio_3, dio_din = (
            pad_xy(parts[f"D{4+n}"], 1),
            pad_xy(parts[f"D{4+n}"], 2),
            pad_xy(parts[f"D{4+n}"], 3),
        )
        screw = pad_xy(j8, n + 1)
        route(board, inn, [
            screw, (rpu_in[0], screw[1]), rpu_in, (rpu_in[0], 33.20),
            (rser_in[0], 33.20), rser_in,
        ], 0.2)
        route(board, din, [rser_din, (cap_din[0], rser_din[1]), cap_din], 0.2)
        route(board, din, [cap_din, (dio_din[0], cap_din[1]), dio_din], 0.2)
        gnd_via(board, gnd, cap_g[0], cap_g[1])
        gnd_via(board, gnd, dio_g[0], dio_g[1])

        hdr = pad_xy(j2, pin)
        # D5 and D6 sit on the pin column, so the run is straight.
        # D7 and D8 jog left into the next pins.
        if n == 3:
            route(board, din, [dio_din, (dio_din[0], 24.2), (hdr[0], 24.2), hdr], 0.2)
        elif n == 4:
            route(board, din, [dio_din, (dio_din[0], 23.2), (hdr[0], 23.2), hdr], 0.2)
        else:
            route(board, din, [dio_din, hdr], 0.2)

        taps.append((sx - 2.60, rpu_3, dio_3))

    # Up from the screw-edge lane, beside the screw, on the front.
    for tap, rpu_3, dio_3 in taps:
        route(board, v3, [rpu_3, (tap, rpu_3[1]), (tap, dio_3[1]), dio_3], 0.2)
        route(board, v3, [(tap, V3_EDGE_Y), (tap, rpu_3[1])], 0.2)


def atlas_modules(board):
    """Atlas EZO boards for the 3D viewer. No pads, and not in the BOM.

    Each model is the datasheet outline, 13.97 by 20.16 mm, with the two
    male headers 17.78 mm apart. The top of the model is lifted so the
    header body sits on the socket.
    """
    folder = "/home/mdahlgre/src/Pool-Controller/hardware/sensor-hat/SensorHat.pretty"
    specs = (
        ("EZO1", "pH", 8.96, "${KIPRJMOD}/3d/Atlas_EZO_pH.step"),
        ("EZO2", "ORP", 24.96, "${KIPRJMOD}/3d/Atlas_EZO_ORP.step"),
        ("EZO3", "EZO", 40.775, "${KIPRJMOD}/3d/Atlas_EZO_EZO.step"),
    )
    for ref, value, x, filename in specs:
        fp = load_fp(folder, "Atlas_EZO")
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(vec(x, 24.29))
        models = fp.Models()
        if len(models) != 1:
            raise SystemExit(f"{ref} model count {len(models)}")
        models[0].m_Filename = filename
        board.Add(fp)


def ssd1309(board):
    """2.42 inch SSD1309 for the 3D viewer. No pads, and not in the BOM.

    The module outline is the MC242GX: 72 by 43 mm, header on the short edge.
    Turned so that header is vertical, the glass lies across the right side
    of the hat, about 4 mm clear of the Atlas boards, and stops above the
    screw terminals. About 10 mm hangs off the USB edge, and about 6.5 mm
    hangs off the antenna edge. Pin 5 (reset) is not fitted.
    """
    folder = "/home/mdahlgre/src/Pool-Controller/hardware/sensor-hat/SensorHat.pretty"
    fp = load_fp(folder, "SSD1309")
    fp.SetReference("DISP1")
    fp.SetValue("SSD1309")
    fp.SetPosition(vec(58.5, 9.5))
    fp.SetOrientationDegrees(-90)
    board.Add(fp)


def silk(board, text, x, y, size=1.0, thickness=0.15):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(vec(x, y))
    item.SetLayer(pcbnew.F_SilkS)
    item.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    item.SetTextThickness(mm(thickness))
    board.Add(item)
    return item


def buttons(board, names):
    """Two push buttons at the USB-left corner, for the display.

    Each switch closes its GPIO to ground. A 10k pulls that net up to
    the fused 3.3 V. Pin 1 is the USB-side pair and carries the GPIO.
    Pin 2 goes to ground. SW1 (silk A) is GPIO7 on J1 pin 10. SW2
    (silk B) is GPIO6 on J1 pin 12. A stays on the outer top lane and
    B on the inner lane, so the two traces do not cross.
    J17 is on the USB edge, pin 1 at 35 mm from the left. Left to right
    the pins are SW1, ground, SW2, ground, so an enclosure switch across
    each pair does what the matching button does.
    """
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    sw_lib = "/usr/share/kicad/footprints/Button_Switch_SMD.pretty"
    sw_name = "SW_Push_1P1T_XKB_TS-1187A"
    sw_id = ("Button_Switch_SMD", sw_name)
    gnd = ensure_net(board, names, "GND")
    v3 = ensure_net(board, names, "V3OUT")
    btn1 = ensure_net(board, names, "BTN1")
    btn2 = ensure_net(board, names, "BTN2")

    def set_numbered(fp, number, net):
        found = False
        for pad in fp.Pads():
            if pad.GetNumber() == str(number):
                pad.SetNet(net)
                found = True
        if not found:
            raise SystemExit(f"{fp.GetReference()} missing pad {number}")

    sw1 = add_part(board, names, sw_lib, sw_name, "SW1", "push", 8.0, 5.2, 0, ["GND", "BTN1"], sw_id)
    sw2 = add_part(board, names, sw_lib, sw_name, "SW2", "push", 19.0, 5.2, 0, ["GND", "BTN2"], sw_id)
    for sw, sig in ((sw1, btn1), (sw2, btn2)):
        set_numbered(sw, "1", sig)
        set_numbered(sw, "2", gnd)
        sw.Value().SetVisible(False)
    style_text(sw1.Reference(), 8.0, 8.7, 0.55)
    style_text(sw2.Reference(), 19.0, 8.7, 0.55)
    silk(board, "A", 4.2, 5.2, 0.9, 0.15)
    silk(board, "B", 22.9, 5.2, 0.9, 0.15)

    # Pin 1 at the left. Rotation puts the row along the USB edge.
    j17 = add_part(
        board, names, HDR_LIB, "PinHeader_1x04_P2.54mm_Vertical",
        "J17", "external", 35.0, 2.10, 90,
        ["BTN1", "GND", "BTN2", "GND"],
        ("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    )
    j17.Value().SetVisible(False)
    style_text(j17.Reference(), 33.1, 4.7, 0.45)
    silk(board, "A", 36.27, 4.55, 0.7, 0.12)
    silk(board, "B", 41.35, 4.55, 0.7, 0.12)
    a_pin, b_pin = pad_xy(j17, 1), pad_xy(j17, 3)
    route(board, btn1, [a_pin, (a_pin[0], 0.75)], 0.2)
    route(board, btn2, [b_pin, (b_pin[0], 1.5)], 0.2)

    r29 = add_part(
        board, names, R_LIB, "R_0805", "R29", "10k", 8.0, 11.3, 90,
        ["V3OUT", "BTN1"], ("PCM_JLCPCB", "R_0805"),
    )
    r30 = add_part(
        board, names, R_LIB, "R_0805", "R30", "10k", 17.5, 11.3, 90,
        ["V3OUT", "BTN2"], ("PCM_JLCPCB", "R_0805"),
    )
    style_text(r29.Reference(), 6.3, 11.3, 0.4)
    style_text(r29.Value(), 9.7, 11.3, 0.4)
    style_text(r30.Reference(), 15.8, 11.3, 0.4)
    style_text(r30.Value(), 19.2, 11.3, 0.4)

    def pads(fp, number):
        return [
            (pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y))
            for pad in fp.Pads()
            if pad.GetNumber() == str(number)
        ]

    for sw, sig in ((sw1, btn1), (sw2, btn2)):
        sig_pads = pads(sw, 1)
        gnd_pads = pads(sw, 2)
        route(board, sig, sig_pads, 0.2)
        route(board, gnd, gnd_pads, 0.2)
        outer = min(gnd_pads, key=lambda point: point[0])
        route(board, gnd, [outer, (outer[0] - 1.3, outer[1])], 0.2)
        gnd_via(board, gnd, outer[0] - 1.3, outer[1])

    left_v = pad_xy(fps["J12"], 1)
    pull_y = pad_xy(r29, 1)[1]
    route(board, v3, [left_v, (left_v[0], 24.2), (1.8, 24.2), (1.8, pull_y), pad_xy(r30, 1)], 0.30)

    gpio7 = pad_xy(fps["J1"], 10)
    route(board, btn1, [(5.0, 3.325), (12.2, 3.325)], 0.2)
    route(board, btn1, [(12.2, 0.75), (12.2, 10.39), (pad_xy(r29, 2)[0], 10.39)], 0.2)
    route(board, btn1, [(12.2, 0.75), (gpio7[0], 0.75), gpio7], 0.2)

    gpio6 = pad_xy(fps["J1"], 12)
    route(board, btn2, [(14.5, 3.325), (22.4, 3.325), (22.4, 10.39), pad_xy(r30, 2)], 0.2)
    route(board, btn2, [(22.4, 1.5), (gpio6[0], 1.5), gpio6], 0.2)


def main():
    board = pcbnew.BOARD()
    rect(board, 0, 0, BOARD_W, BOARD_H, pcbnew.Edge_Cuts, 0.1)
    names = {}
    socket(board, names, "J1", USB_ROW_Y, USB_NETS)
    socket(board, names, "J2", RELAY_ROW_Y, RELAY_NETS)
    # EZO circuits side by side on the left. Same data-row height, so both
    # 20.16 mm boards clear the Pico header and each other. Probe row is
    # 17.78 mm toward the screw edge.
    ezo_y = 15.4
    ezo_pair(board, names, "J11", "J12", 6.42, ezo_y, "EZO_PH_TX", "EZO_PH_RX", "PH_PRB", "PH_PGND")
    ezo_pair(board, names, "J9", "J10", 22.42, ezo_y, "EZO_ORP_TX", "EZO_ORP_RX", "ORP_PRB", "ORP_PGND")
    # Just left of the equal gap, so the socket courtyard clears J16.
    # The body may cover the Pico pins. The socket holes stay off those pins.
    ezo_pair(board, names, "J13", "J14", 38.235, ezo_y, "SDA", "SCL", "EZO_PRB", "EZO_PGND")

    # Each probe screw is centered under its module. J5 stops 1 mm short of
    # the 1-Wire body, so it sits slightly left of the I2C module's center.
    plug(board, names, "J3", "pH probe", 4.80, 41.8, 2, ["PH_PRB", "PH_PGND"], (7.35, 46.15))
    plug(board, names, "J4", "ORP probe", 23.27, 41.8, 2, ["ORP_PRB", "ORP_PGND"], (25.82, 46.15))
    plug(board, names, "J5", "EZO probe", 40.14, 41.8, 2, ["EZO_PRB", "EZO_PGND"], (42.69, 46.15))
    plug(board, names, "J6", "1-Wire", 51.54, 41.8, 3, ["V3OUT", "OW", "GND"], (56.63, 46.15))
    plug(board, names, "J7", "contacts", 68.83, 41.8, 5, ["GND", "IN1", "IN2", "IN3", "IN4"], (79.00, 46.15))
    plug(board, names, "J8", "4-20 mA", 96.28, 41.8, 5, ["GND", "SIG1", "SIG2", "SIG3", "SIG4"], (106.45, 46.15))

    onewire(board, names)
    ma420(board, names)
    ezo(board, names)
    i2c(board, names)
    buttons(board, names)
    contacts(board, names)
    atlas_modules(board)
    ssd1309(board)

    silk(board, "USB edge", 30, 7.2, 0.9)
    silk(board, "antenna", 108, 14.6, 0.8)
    silk(board, "pH", 2.2, 21.6, 0.8)
    silk(board, "ORP", 24.0, 21.4, 0.8)
    silk(board, "EZO", 29.0, 17.4, 0.8)
    silk(board, "PH", 9.62, 29.4, 2.0, 0.15)
    silk(board, "ORP", 25.15, 29.4, 2.0, 0.15)
    silk(board, "EZO", 41.335, 29.4, 2.0, 0.15)
    silk(board, "Pool Controller 1.1", 70.5, 18, 3.0, 0.3)
    silk(board, "PoolVeras", 70.5, 14, 6.0, 0.3)
    # Names sit on the edge. Pin names sit just above them.
    # Pitch is 5.08 mm, so the short names fit a pin.
    for text, x, y in (
        ("pH", 7.34, 48.28),
        ("ORP", 25.81, 48.55),
        ("EZO", 42.68, 48.55),
        ("1-Wire", 56.62, 48.55),
        ("contacts", 78.99, 48.55),
        ("4-20", 106.44, 48.55),
    ):
        silk(board, text, x, y, 0.6, 0.12)
    pin_labels = (
        (4.80, ("PRB", "PGND")),
        (23.27, ("PRB", "PGND")),
        (40.14, ("PRB", "PGND")),
        (51.54, ("3V3", "DATA", "GND")),
        (68.83, ("GND", "1", "2", "3", "4")),
        (96.28, ("GND", "1", "2", "3", "4")),
    )
    for origin, labels in pin_labels:
        for index, text in enumerate(labels):
            silk(board, text, origin + index * 5.08, 47.85, 0.5, 0.1)
    silk(board, "Pico 40", 104.5, 6.4, 0.6)
    silk(board, "Pico 1", 100.0, 19.0, 0.7)
    silk(board, "17.78 mm", 13.5, 18.5, 0.7)

    # Pin-1 marks on the top silk, above the square pads.
    for y in (USB_ROW_Y, RELAY_ROW_Y):
        segment(board, PIN1_X - 1.2, y + 1.4, PIN1_X + 1.2, y + 1.4, pcbnew.F_SilkS)
        segment(board, PIN1_X + 1.2, y + 1.4, PIN1_X + 1.2, y - 1.4, pcbnew.F_SilkS)
        segment(board, PIN1_X + 1.2, y - 1.4, PIN1_X - 1.2, y - 1.4, pcbnew.F_SilkS)
        segment(board, PIN1_X - 1.2, y - 1.4, PIN1_X - 1.2, y + 1.4, pcbnew.F_SilkS)

    title = board.GetTitleBlock()
    title.SetTitle("Pool sensor hat example")
    title.SetComment(0, "J1 and J2 are on the bottom. Pin 1 of each is the antenna end.")
    title.SetComment(1, "Rows are 17.78 mm apart. Pitch along a row is 2.54 mm.")
    title.SetComment(2, "J9/J10, J11/J12, and J13/J14 are EZO sockets, 17.78 mm apart, on the top.")
    title.SetComment(3, "Back is ground. F1 feeds every 3.3 V load on this board.")
    ground_plane(board, names)
    pcbnew.SaveBoard(OUT, board)
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
