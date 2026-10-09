#!/usr/bin/env python3
"""Example board: outline, Pico sockets, screw terminals, and EZO sockets.

The 1-Wire, 4-20 mA, pH, ORP, I2C EZO, and contact circuits are placed and routed.
The back is a ground plane. Header ground pins are already common on the
Waveshare board, so the plane is the only ground wiring.
Header 3.3 V pins are common there too. Each load uses the nearest pin.
Three EZO circuits plug into female 1x3 sockets on the top. pH and ORP are
UART. The third is I2C on SDA and SCL, with 4.7k pull-ups fitted.
J16 is the same I2C bus, under J1 pins 12 through 15, and is not fitted.
Pin 1 is 3.3 V and faces the fuse.
Parts may sit under those boards. Each probe screw is only the two probe wires.
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
# IO4 stays on the center line. The USB-row sockets are on the back,
# 3.5 mm from their edge. GPIO4 (IO4) is J1 pin 15.
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

# Pin 1 is the antenna end. 4-20 uses USB pins 6, 7, 9, 10. Contacts use
# relay pins 4, 5, 7, 9. pH UART is relay pins 20 and 19. ORP UART is USB
# pins 16 and 17. I2C is USB pins 15 and 14. Pin 20 on the USB row is the
# buzzer, so it stays open. Pin 11 is the fuse input.
USB_NETS = [
    None, None, "GND", "+3V3", "+3V3", "ADC4", "ADC3", "GND", "ADC2", "ADC1",
    "+3V3", None, "GND", "SCL", "SDA", "EOR_RX", "EOR_TX", "GND", None, None,
]
RELAY_NETS = [
    None, None, "GND", "DIN4", "DIN3", None, "DIN2", "GND", "DIN1", None,
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
    the fused output. V3OUT drops between relay pins 18 and 19 and runs
    straight to J14 pin 1. The other 3.3 V loads branch off that run.
    """
    parts = {}
    # Rotation 180 puts the 3.3 V input on pin 11 and the output to its left.
    # The body is between the rows, clear of both courtyards.
    parts["F1"] = add_part(
        board, names, FUSE_LIB, "Fuse_1812_4532Metric",
        "F1", "0.2A", 68.02, 15.6, 180, ["+3V3", "V3OUT"],
        ("Fuse", "Fuse_1812_4532Metric"),
    )
    parts["C3"] = add_part(
        board, names, R_LIB, "C_0805",
        "C3", "100nF", 61.2, 16.55, 270, ["V3OUT", "GND"],
        ("PCM_JLCPCB", "C_0805"),
    )
    # Odd pins are the pull-ups. Even pins are the data net. Pin 1 is the
    # header end. The pull-up column sits on J6 pin 1 so the 3.3 V feed is
    # one vertical. JP6 and R21 keep their place beside that column.
    jp_y = 28.3
    pull_x = 51.54 + 0.91
    jp_x = pull_x + 6.2
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
    # Between the header pin and the jumper's data column. Pad 2 faces the pin.
    parts["R21"] = add_part(
        board, names, R_LIB, "R_0805",
        "R21", "100", jp_x + 1.59, 25.0, 180, ["OW", "OWGPIO"],
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
    # F1's output is 0.25 mm. It runs to the drop, then cuts down onto R27.
    route(board, v3, [f_out, (drop_x, f_out[1]), (48.51, 13.0), (45.0, 13.0)], 0.25)
    route(board, v3, [(drop_x, f_out[1]), (drop_x, socket_y), (j14_v[0], socket_y)], 0.25)
    # J6 pin 1 and the pull-up pads share an x, so this rise has no jog.
    # The clamp feeds leave J6 along the screw edge. They do not tour the left side.
    v_pads = [pad_xy(parts[ref], 1) for ref, *_ in pullups]
    j7_tap = pad_xy(fps["J8"], 5)[0] - 2.60
    route(board, v3, [(drop_x, socket_y), v_pads[0], conn_v, (conn_v[0], V3_EDGE_Y), (j7_tap, V3_EDGE_Y)], 0.25)
    route(board, v3, v_pads, 0.2)
    for ref, _value, net, row in pullups:
        src = pad_xy(parts[ref], 2)
        dst = pad_xy(parts["JP6"], 1 + 2 * row)
        route(board, ensure_net(board, names, net), [src, dst], 0.2)

    ow_pins = [pad_xy(parts["JP6"], n) for n in (2, 4, 6)]
    route(board, ow, ow_pins, 0.25)
    # Cut the corner into J6 instead of running along the terminal.
    route(board, ow, [ow_pins[2], (ow_pins[2][0], 37.23), conn_ow], 0.25)
    route(board, ow, [r21_ow, (r21_ow[0], ow_pins[0][1]), ow_pins[0]], 0.25)
    # Cut the corner into the header pin instead of running across at the resistor.
    route(board, owgpio, [r21_gpio, (r21_gpio[0], 23.15), ow_gpio], 0.25)

    style_text(parts["F1"].Reference(), 68.02, 18.15, 0.55)
    style_text(parts["F1"].Value(), 68.02, 18.85, 0.5)
    style_text(parts["C3"].Reference(), 58.6, 16.55, 0.5)
    style_text(parts["C3"].Value(), 58.6, 17.35, 0.45)
    parts["JP6"].Value().SetVisible(False)
    style_text(parts["JP6"].Reference(), jp_x - 8.8, 27.5, 0.55)
    fps["J6"].Reference().SetPosition(vec(56.63, 46.15))
    style_text(parts["R21"].Reference(), jp_x - 2.11, 25.6, 0.45)
    style_text(parts["R21"].Value(), jp_x - 2.11, 24.8, 0.4)
    # The big row labels are the shunt choice. Keep the part numbers, hide the tiny values.
    label_x = jp_x + 4.4
    label_size = 1.60
    for ref, value, _net, row in pullups:
        y = jp_y + row * PITCH
        parts[ref].Value().SetVisible(False)
        style_text(parts[ref].Reference(), pull_x + 2.6, y, 0.4)
        item = silk(board, value, label_x, y, label_size, 0.18)
        item.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        item.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
        item.SetPosition(vec(label_x, y))


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
    3.3 V is V3OUT, from the fuse drop. The ADC runs on the front,
    between the header rows.
    """
    j7 = next(fp for fp in board.GetFootprints() if fp.GetReference() == "J8")
    sig_x = [pad_xy(j7, n)[0] for n in range(2, 6)]
    # ADC pins on the USB row, left to right: GPIO7, GPIO8, GPIO9, GPIO10.
    adc_pin = [10, 9, 7, 6]
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
    j1, j7 = fps["J1"], fps["J8"]
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

    # Each channel leaves the clamp on a short rise, cuts onto its lane,
    # runs left, then cuts up into the header pin.
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
        adc_pad = pad_xy(j1, pin)
        rise_y, join_x, end_x, pin_y = cut

        route(board, sig, [conn, (r_sig[0], conn[1]), r_sig, series_sig], 0.25)
        route(board, adc, [series_adc, (series_adc[0], clamp_a[1]), clamp_a], 0.2)
        route(board, adc, [cap_a, (series_adc[0], cap_a[1])], 0.2)
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
        "R20": (36.2, 6.4, ["EZO_ORP_RX", "EOR_TX"]),
        "R19": (32.4, 5.0, ["EZO_ORP_TX", "EOR_RX"]),
        "R18": (20.41, 17.0, ["EZO_PH_RX", "EPH_TX"]),
        "R17": (28.59, 19.0, ["EZO_PH_TX", "EPH_RX"]),
    }
    parts = {}
    for ref, (x, y, nets) in placed.items():
        parts[ref] = add_part(
            board, names, R_LIB, "R_0805", ref, "100", x, y, 0, nets,
            ("PCM_JLCPCB", "R_0805"),
        )
        style_text(parts[ref].Reference(), x, y - 1.35, 0.4)
        style_text(parts[ref].Value(), x, y + 1.35, 0.4)
    # The upper ORP part is close to the header, so its name sits beside it.
    style_text(parts["R19"].Reference(), 32.4, 6.2, 0.4)
    style_text(parts["R19"].Value(), 29.4, 5.0, 0.4)
    style_text(parts["R20"].Reference(), 36.2, 7.7, 0.4)
    style_text(parts["R20"].Value(), 39.0, 6.4, 0.4)

    v3 = ensure_net(board, names, "V3OUT")

    def wire(net_name, points):
        route(board, ensure_net(board, names, net_name), points, 0.25)

    # Same-x pairs are a straight drop. The others cut the corner.
    wire("PH_PGND", [pad_xy(fps["J12"], 3), pad_xy(fps["J3"], 2)])
    ph_prb, ph_screw = pad_xy(fps["J12"], 2), pad_xy(fps["J3"], 1)
    wire("PH_PRB", [ph_prb, (ph_prb[0], 31.4), (ph_screw[0], 33.94), ph_screw])
    orp_prb, orp_screw = pad_xy(fps["J10"], 2), pad_xy(fps["J4"], 1)
    wire("ORP_PRB", [orp_prb, (orp_prb[0], 32.0), (orp_screw[0], 34.54), orp_screw])
    wire("ORP_PGND", [pad_xy(fps["J10"], 3), pad_xy(fps["J4"], 2)])
    ezo_prb, ezo_screw = pad_xy(fps["J14"], 2), pad_xy(fps["J5"], 1)
    wire("EZO_PRB", [ezo_prb, (ezo_prb[0], 31.56), (ezo_screw[0], 34.8), ezo_screw])
    ezo_pg, ezo_pg_screw = pad_xy(fps["J14"], 3), pad_xy(fps["J5"], 2)
    wire("EZO_PGND", [ezo_pg, (ezo_pg[0], 34.0), (ezo_pg_screw[0], 34.76), ezo_pg_screw])

    # Probe power is one run just above the sockets. J14 pin 1 is fed
    # straight from the fuse; pH and ORP tie onto that same run.
    bus_y = 24.2
    v_pads = [pad_xy(fps[ref], 1) for ref in ("J12", "J10", "J14")]
    route(board, v3, [(v_pads[0][0], bus_y), (v_pads[-1][0], bus_y)], 0.25)
    for pad in v_pads:
        route(board, v3, [(pad[0], bus_y), pad], 0.25)

    # Socket grounds are through-hole and meet the back plane.
    # pH: socket pin 2 is the left data pin and goes to the left header pin.
    # Each run cuts onto the resistor lane, then cuts into the header pin.
    ph = (
        ("R17", 2, 20, 18.34, 45.02),
        ("R18", 3, 19, 18.88, 45.56),
    )
    for ref, sock_pin, header_pin, sock_knee, pin_knee in ph:
        src = pad_xy(fps["J11"], sock_pin)
        left = pad_xy(parts[ref], 1)
        right = pad_xy(parts[ref], 2)
        dst = pad_xy(j2, header_pin)
        net_in = parts[ref].FindPadByNumber("1").GetNet()
        net_out = parts[ref].FindPadByNumber("2").GetNet()
        route(board, net_in, [src, (sock_knee, left[1]), left], 0.2)
        route(board, net_out, [right, (pin_knee, right[1]), dst], 0.2)

    # Receive on the upper lane, transmit on the lower. Each end is a
    # short diagonal so the run does not travel the whole pin column.
    rx_src = pad_xy(fps["J9"], 2)
    rx_left, rx_right = pad_xy(parts["R19"], 1), pad_xy(parts["R19"], 2)
    rx_dst = pad_xy(j1, 16)
    rx_net_in = parts["R19"].FindPadByNumber("1").GetNet()
    rx_net = parts["R19"].FindPadByNumber("2").GetNet()
    route(board, rx_net_in, [rx_src, (28.81, rx_left[1]), rx_left], 0.2)
    # Over the header, then a short diagonal into pin 16.
    route(board, rx_net, [
        rx_right, (35.0, rx_right[1]), (38.0, 2.0), (56.0, 2.0), rx_dst,
    ], 0.2)

    tx_src = pad_xy(fps["J9"], 3)
    tx_left, tx_right = pad_xy(parts["R20"], 1), pad_xy(parts["R20"], 2)
    tx_dst = pad_xy(j1, 17)
    tx_net_in = parts["R20"].FindPadByNumber("1").GetNet()
    tx_net = parts["R20"].FindPadByNumber("2").GetNet()
    route(board, tx_net_in, [tx_src, (29.95, tx_left[1]), tx_left], 0.2)
    route(board, tx_net, [tx_right, (52.02, tx_right[1]), tx_dst], 0.2)


def i2c(board, names):
    """Third EZO on SDA and SCL, plus an unfitted header on that bus.

    J16 pin 1 is 3.3 V, on the right, under the empty pin next to the fuse.
    Pin 2 is ground under J1 pin 13. Pin 3 is SCL under pin 14. Pin 4 is
    SDA under pin 15. The holes are empty.
    """
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    j1 = fps["J1"]
    sda_pin, scl_pin = pad_xy(j1, 15), pad_xy(j1, 14)
    # Pin 1 on the right, toward the fuse. Pins step left onto pins 13, 14, 15.
    header_y = 9.2
    j6_x = pad_xy(j1, 12)[0]
    j6 = add_part(
        board, names, HDR_LIB, "PinHeader_1x04_P2.54mm_Vertical",
        "J16", "DNP", j6_x, header_y, 270, ["V3OUT", "GND", "SCL", "SDA"],
        ("Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical"),
    )
    j6.SetDNP(True)
    j6.Value().SetVisible(False)
    label_x = j6_x - 3 * PITCH - 2.5
    style_text(j6.Reference(), label_x, header_y - 0.7, 0.45)
    silk(board, "DNP", label_x, header_y + 0.5, 0.45, 0.1)
    for index, text in enumerate(("3V3", "GND", "SCL", "SDA")):
        silk(board, text, j6_x - index * PITCH, header_y - 2.15, 0.45, 0.1)
    sock_sda = pad_xy(fps["J13"], 2)
    sock_scl = pad_xy(fps["J13"], 3)

    # R27 lies on the fuse trunk. R28 stands on that same trunk.
    r27 = add_part(
        board, names, R_LIB, "R_0805", "R27", "4.7k", 44.09, 13.0, 180,
        ["V3OUT", "SDA"], ("PCM_JLCPCB", "R_0805"),
    )
    f_out = pad_xy(fps["F1"], 2)
    r28 = add_part(
        board, names, R_LIB, "R_0805", "R28", "4.7k", 54.0, f_out[1] - 0.95, 90,
        ["V3OUT", "SCL"], ("PCM_JLCPCB", "R_0805"),
    )
    style_text(r27.Reference(), 43.0, 12.0, 0.4)
    style_text(r27.Value(), 45.0, 12.0, 0.4)
    style_text(r28.Reference(), 52.6, f_out[1] - 2.3, 0.4)
    style_text(r28.Value(), 52.6, f_out[1] - 1.4, 0.4)

    v3 = ensure_net(board, names, "V3OUT")
    sda = ensure_net(board, names, "SDA")
    scl = ensure_net(board, names, "SCL")
    gnd = ensure_net(board, names, "GND")
    scl_lane = pad_xy(r28, 2)[1]
    sda_pad = pad_xy(r27, 2)
    j6_sda, j6_scl = pad_xy(j6, 4), pad_xy(j6, 3)

    # SDA rises off R27, into the socket, then across to the header at y=6.
    route(board, sda, [sda_pin, j6_sda], 0.2)
    route(board, sda, [
        sda_pad, (43.18, 8.26), sock_sda, (43.44, 6.56), (44.0, 6.0), (sda_pin[0], 6.0),
    ], 0.2)
    route(board, scl, [
        scl_pin, j6_scl, (58.0, scl_lane), (sock_scl[0], scl_lane), sock_scl,
    ], 0.2)

    # R27's 3.3 V pad is the end of the fuse trunk. R28's pad sits on that trunk.

    # Ground drops straight from pin 13 into J16 pin 2.
    gnd_pin = pad_xy(j1, 13)
    j6_gnd = pad_xy(j6, 2)
    route(board, gnd, [gnd_pin, j6_gnd], 0.2)
    gnd_via(board, gnd, *j6_gnd)

    # Fused 3.3 V from the fuse output, cutting the corner into J16 pin 1.
    j6_v = pad_xy(j6, 1)
    route(board, v3, [f_out, (f_out[0], 13.12), (j6_v[0], 11.38), j6_v], 0.2)


def contacts(board, names):
    """Dry contacts on J7. 10k to 3.3 V, 1k, 100 nF, and a clamp.

    3.3 V is V3OUT from the fuse drop. Ground vias drop into the
    back plane. D5 goes to relay pin 9, D6 to pin 7, D7 to pin 5, D8 to pin 4.
    """
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    j2, j8 = fps["J2"], fps["J7"]
    columns = [pad_xy(j8, n)[0] for n in range(2, 6)]
    # Left to right on the screws. D5 (IN1) is pin 9, D6 (IN2) is pin 7.
    # IN3 stays on pin 5, IN4 on pin 4.
    header_pins = [9, 7, 5, 4]
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
        # D5 and D6 now sit on the pin column, so the run is straight.
        # D7 and D8 keep the short jog into their pins.
        if n == 3:
            route(board, din, [dio_din, (dio_din[0], 23.0), (hdr[0], 22.61), hdr], 0.2)
        elif n == 4:
            route(board, din, [dio_din, (dio_din[0], 23.4), hdr], 0.2)
        else:
            route(board, din, [dio_din, hdr], 0.2)

        taps.append((sx - 2.60, rpu_3, dio_3))

    # Up from the screw-edge lane, beside the screw, on the front.
    for tap, rpu_3, dio_3 in taps:
        route(board, v3, [rpu_3, (tap, rpu_3[1]), (tap, dio_3[1]), dio_3], 0.2)
        route(board, v3, [(tap, V3_EDGE_Y), (tap, rpu_3[1])], 0.2)


def silk(board, text, x, y, size=1.0, thickness=0.15):
    item = pcbnew.PCB_TEXT(board)
    item.SetText(text)
    item.SetPosition(vec(x, y))
    item.SetLayer(pcbnew.F_SilkS)
    item.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    item.SetTextThickness(mm(thickness))
    board.Add(item)
    return item


def main():
    board = pcbnew.BOARD()
    rect(board, 0, 0, BOARD_W, BOARD_H, pcbnew.Edge_Cuts, 0.1)
    names = {}
    socket(board, names, "J1", USB_ROW_Y, USB_NETS)
    socket(board, names, "J2", RELAY_ROW_Y, RELAY_NETS)
    # EZO circuits side by side on the left. Same data-row height, so both
    # 20.16 mm boards clear the Pico header and each other. Probe row is
    # 17.78 mm toward the screw edge.
    ezo_y = 8.0
    ezo_pair(board, names, "J11", "J12", 4.80, ezo_y, "EZO_PH_TX", "EZO_PH_RX", "PH_PRB", "PH_PGND")
    ezo_pair(board, names, "J9", "J10", 23.27, ezo_y, "EZO_ORP_TX", "EZO_ORP_RX", "ORP_PRB", "ORP_PGND")
    # Just left of the equal gap, so the socket courtyard clears J16.
    # The body may cover the Pico pins. The socket holes stay off those pins.
    ezo_pair(board, names, "J13", "J14", 40.90, ezo_y, "SDA", "SCL", "EZO_PRB", "EZO_PGND")

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
    contacts(board, names)

    silk(board, "USB edge", 18, 5.2, 0.9)
    silk(board, "antenna", 108, 14.6, 0.8)
    silk(board, "IO4", IO4_X + 3.2, 1.3, 0.8)
    silk(board, "pH", 2.2, 14.2, 0.8)
    silk(board, "ORP", 24.0, 14.0, 0.8)
    silk(board, "EZO", 29.0, 10.0, 0.8)
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

    # Short mark from the IO4 pad toward the USB edge.
    segment(board, IO4_X, 0.4, IO4_X, USB_ROW_Y - 1.6, pcbnew.F_SilkS)

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
