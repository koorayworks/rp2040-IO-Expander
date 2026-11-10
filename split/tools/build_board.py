#!/usr/bin/env python3
"""Build split/zero_board/zero_board.kicad_pcb (placement + nets, unrouted).

Frame: origin at board top-left corner (USB end), x right, y down, mm.
Board: 18.0 x 23.5, 4 layers. All coordinates from verified sources:
- edge pads: official STEP extraction (2026-10-31)
- USB-C position: REV.A proven placement (9.00, 4.77)
- buttons / LED: STEP centers (same as REV.A)
- FFC: FH34SRJ-30S at the RP2040 chip site, cable exit downward (SPLIT_SPEC 2026-11-03)
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
OUT = os.path.join(ROOT, 'split', 'zero_board')
os.makedirs(OUT, exist_ok=True)
mm = pcbnew.FromMM
STD = '/usr/share/kicad/footprints'

def lset(*layers):
    s = pcbnew.LSET()
    for l in layers:
        s.AddLayer(l)
    return s

# ---------------- frozen 30P channel map (design-time freeze, 2026-11-10) ----
# channel -> net, channel 1 at the left when looking at the populated face
# with the cable exiting downward.
CHANNELS = [
    'VSYS', 'GND', '3V3', 'GPIO29', 'GPIO28', 'GPIO27', 'GPIO26', 'GPIO15',
    'GPIO14', 'GPIO13', 'GPIO12', 'GPIO11', 'GPIO10', 'GPIO9', 'GPIO8',
    'GPIO7', 'GPIO6', 'GPIO5', 'GPIO4', 'GPIO3', 'GPIO2', 'GPIO1', 'GPIO0',
    'GND', 'USB_D-', 'USB_D+', 'GND', 'BOOT', 'RESET', 'STATUS_LED',
]
assert len(CHANNELS) == 30

EDGE = [  # (net, hole_x, hole_y) STEP-verified
    ('VSYS', 1.38, 1.59), ('GND', 1.38, 4.13), ('3V3', 1.38, 6.67),
    ('GPIO29', 1.38, 9.21), ('GPIO28', 1.38, 11.75), ('GPIO27', 1.38, 14.29),
    ('GPIO26', 1.38, 16.83), ('GPIO15', 1.38, 19.37), ('GPIO14', 1.38, 21.92),
    ('GPIO13', 3.92, 21.92), ('GPIO12', 6.46, 21.92), ('GPIO11', 9.00, 21.92),
    ('GPIO10', 11.54, 21.92), ('GPIO9', 14.08, 21.92),
    ('GPIO8', 16.62, 21.92), ('GPIO7', 16.62, 19.37), ('GPIO6', 16.62, 16.83),
    ('GPIO5', 16.62, 14.29), ('GPIO4', 16.62, 11.75), ('GPIO3', 16.62, 9.21),
    ('GPIO2', 16.62, 6.67), ('GPIO1', 16.62, 4.13), ('GPIO0', 16.62, 1.59),
]

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)

nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]

def assign(fp, padnum, netname):
    hit = 0
    for pad in fp.Pads():
        if str(pad.GetNumber()) == str(padnum):
            pad.SetNet(net(netname))
            hit += 1
    return hit

# ---------------- outline ----------------
for (x1, y1, x2, y2) in [(0, 0, 18, 0), (18, 0, 18, 23.5), (18, 23.5, 0, 23.5), (0, 23.5, 0, 0)]:
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.05))
    board.Add(s)

# ---------------- ZeroEdge23 ----------------
edge = pcbnew.FOOTPRINT(board)
edge.SetFPID(pcbnew.LIB_ID('split', 'ZeroEdge23'))
edge.SetReference('J1')
for i, (nname, hx, hy) in enumerate(EDGE, start=1):
    if nname == 'GPIO14':
        dx, dy, sx, sy = 0.30, 0.0, 2.4, 1.7
    elif nname == 'GPIO8':
        dx, dy, sx, sy = -0.30, 0.0, 2.4, 1.7
    elif hx < 9:
        dx, dy, sx, sy = 0.30, 0.0, 2.4, 1.7
    elif hy > 21:
        dx, dy, sx, sy = 0.0, -0.30, 1.7, 2.4
    else:
        dx, dy, sx, sy = -0.30, 0.0, 2.4, 1.7
    pad = pcbnew.PAD(edge)
    pad.SetNumber(str(i))
    pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetSize(pcbnew.VECTOR2I(mm(sx), mm(sy)))
    pad.SetPosition(pcbnew.VECTOR2I(mm(hx + dx), mm(hy + dy)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
    pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
    pad.SetOffset(pcbnew.VECTOR2I(mm(-dx), mm(-dy)))
    pad.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask))
    pad.SetNet(net(nname))
    edge.Add(pad)
board.Add(edge)

# ---------------- USB-C (duplicate proven fp from Rev.W) ----------------
src = pcbnew.LoadBoard(os.path.join(ROOT, 'IO_BOARD.kicad_pcb'))
ext = pcbnew.LoadBoard(os.path.join(ROOT, 'ext_board', 'ext_board.kicad_pcb'))
def dup_from(b, match):
    for fp in b.GetFootprints():
        if match in str(fp.GetFPID().GetLibItemName()):
            d = fp.Duplicate()
            return d
    raise RuntimeError('not found: ' + match)

usb = dup_from(src, 'TYPE-C-31-M-12')
usb.SetReference('J2')
usb.SetPosition(pcbnew.VECTOR2I(mm(9.00), mm(4.77)))
usb.SetOrientationDegrees(0)
board.Add(usb)
USBMAP = {'A1': 'GND', 'B1': 'GND', 'A12': 'GND', 'B12': 'GND', 'S1': 'GND',
          'A4': 'USB_VBUS', 'B4': 'USB_VBUS', 'A9': 'USB_VBUS', 'B9': 'USB_VBUS',
          'A6': 'USB_D+_C', 'B6': 'USB_D+_C', 'A7': 'USB_D-_C', 'B7': 'USB_D-_C',
          'A5': 'CC1', 'B5': 'CC2'}
for pn, nn in USBMAP.items():
    assert assign(usb, pn, nn) >= 1, pn

# ---------------- ESD USBLC6-2SC6 ----------------
esd = pcbnew.FootprintLoad(os.path.join(STD, 'Package_TO_SOT_SMD.pretty'), 'SOT-23-6')
esd.SetFPID(pcbnew.LIB_ID('split', 'SOT-23-6'))
esd.SetReference('U1')
esd.SetValue('USBLC6-2SC6')
esd.SetPosition(pcbnew.VECTOR2I(mm(6.30), mm(7.90)))
esd.SetOrientationDegrees(90)
board.Add(esd)
for pn, nn in {'1': 'USB_D-_C', '2': 'GND', '3': 'USB_D+_C', '4': 'USB_D+', '5': 'USB_VBUS', '6': 'USB_D-'}.items():
    assert assign(esd, pn, nn) == 1, pn

# ---------------- CC pull-downs ----------------
for ref, cx, ccnet in (('R1', 6.90, 'CC1'), ('R2', 11.10, 'CC2')):
    r = pcbnew.FootprintLoad(os.path.join(STD, 'Resistor_SMD.pretty'), 'R_0402_1005Metric')
    r.SetFPID(pcbnew.LIB_ID('split', 'R_0402_1005Metric'))
    r.SetReference(ref)
    r.SetValue('5.1k')
    r.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(3.20)))
    r.SetOrientationDegrees(90)
    board.Add(r)
    assert assign(r, '1', ccnet) == 1
    assert assign(r, '2', 'GND') == 1

# ---------------- FH34SRJ-30S builder ----------------
def make_fh34():
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID('split', 'FH34SRJ-30S-0.5SH'))
    for k in range(1, 31):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(k))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetSize(pcbnew.VECTOR2I(mm(0.30), mm(1.60)))
        pad.SetPosition(pcbnew.VECTOR2I(mm((k - 15.5) * 0.5), 0))
        pad.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.F_Mask, pcbnew.F_Paste))
        fp.Add(pad)
    for i, sx in enumerate((-7.75, 7.75)):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(31 + i))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetSize(pcbnew.VECTOR2I(mm(1.20), mm(1.45)))
        pad.SetPosition(pcbnew.VECTOR2I(mm(sx), 0))
        pad.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.F_Mask, pcbnew.F_Paste))
        fp.Add(pad)
    def line(layer, x1, y1, x2, y2, w=0.12):
        s = pcbnew.PCB_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        fp.Add(s)
    for layer in (pcbnew.F_SilkS, pcbnew.F_Fab):
        line(layer, -8.5, -2.45, 8.5, -2.45)
        line(layer, 8.5, -2.45, 8.5, 1.35)
        line(layer, 8.5, 1.35, -8.5, 1.35)
        line(layer, -8.5, 1.35, -8.5, -2.45)
    c = pcbnew.PCB_SHAPE(fp)
    c.SetShape(pcbnew.SHAPE_T_CIRCLE)
    c.SetCenter(pcbnew.VECTOR2I(mm(-7.25), mm(-2.95)))
    c.SetRadius(mm(0.35))
    c.SetLayer(pcbnew.F_SilkS)
    c.SetWidth(mm(0.12))
    fp.Add(c)
    for (x1, y1, x2, y2) in [(-8.7, -2.65, 8.7, -2.65), (8.7, -2.65, 8.7, 1.55), (8.7, 1.55, -8.7, 1.55), (-8.7, 1.55, -8.7, -2.65)]:
        line(pcbnew.F_CrtYd, x1, y1, x2, y2, 0.05)
    return fp

FFC_POS = (9.0, 11.30)
j3 = make_fh34()
j3.SetReference('J3')
j3.SetPosition(pcbnew.VECTOR2I(mm(FFC_POS[0]), mm(FFC_POS[1])))
j3.SetOrientationDegrees(0)
board.Add(j3)
for k in range(1, 31):
    assert assign(j3, str(k), CHANNELS[k - 1]) == 1, k
assign(j3, '31', 'GND'); assign(j3, '32', 'GND')

j4 = make_fh34()
j4.SetReference('J4')
j4.SetPosition(pcbnew.VECTOR2I(mm(FFC_POS[0]), mm(FFC_POS[1])))
board.Add(j4)
j4.Flip(pcbnew.VECTOR2I(mm(FFC_POS[0]), mm(FFC_POS[1])), False)
# After flip, find rotation so that pad k sits at board x = 9.0 - (k-15.5)*0.5
def pad_x(fp, num):
    for pad in fp.Pads():
        if str(pad.GetNumber()) == str(num):
            return pad.GetPosition().x / 1e6
for rot in (0, 180):
    j4.SetOrientationDegrees(rot)
    if abs(pad_x(j4, 1) - 16.25) < 0.01 and abs(pad_x(j4, 30) - 1.75) < 0.01:
        print('J4 (back) rotation fixed at', rot)
        break
else:
    raise RuntimeError('J4 mirror check failed: pad1 x=%s pad30 x=%s' % (pad_x(j4, 1), pad_x(j4, 30)))
for k in range(1, 31):
    assert assign(j4, str(k), CHANNELS[k - 1]) == 1, k
assign(j4, '31', 'GND'); assign(j4, '32', 'GND')

# ---------------- buttons (fp duplicated from REV.A, proven nets) ----------
for ref, cx, rot, sig in (('SW1', 4.51, 0, 'BOOT'), ('SW2', 13.51, 180, 'RESET')):
    sw = dup_from(ext, 'SW-SMD_4P')
    sw.SetReference(ref)
    sw.SetPosition(pcbnew.VECTOR2I(mm(cx), mm(16.01)))
    sw.SetOrientationDegrees(rot)
    board.Add(sw)
    a = assign(sw, '1', sig); b = assign(sw, '2', 'GND')
    print(ref, 'signal pads:', a, 'gnd pads:', b)
    # any remaining pads: pair by number parity fallback -> leave unconnected if 0

# ---------------- LED + decoupling ----------------
led = pcbnew.FootprintLoad(os.path.join(STD, 'LED_SMD.pretty'), 'LED_WS2812B-2020_PLCC4_2.0x2.0mm')
led.SetFPID(pcbnew.LIB_ID('split', 'LED_WS2812B-2020'))
led.SetReference('D1')
led.SetPosition(pcbnew.VECTOR2I(mm(9.01), mm(15.48)))
led.SetOrientationDegrees(0)
board.Add(led)
assign(led, '1', '3V3'); assign(led, '3', 'GND'); assign(led, '4', 'STATUS_LED')

cap = pcbnew.FootprintLoad(os.path.join(STD, 'Capacitor_SMD.pretty'), 'C_0402_1005Metric')
cap.SetFPID(pcbnew.LIB_ID('split', 'C_0402_1005Metric'))
cap.SetReference('C1')
cap.SetValue('100n')
cap.SetPosition(pcbnew.VECTOR2I(mm(11.75), mm(15.90)))
cap.SetOrientationDegrees(90)
board.Add(cap)
assign(cap, '1', '3V3'); assign(cap, '2', 'GND')

# ---------------- GND plane zone on In1 ----------------
zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.In1_Cu)
zone.SetNet(net('GND'))
zone.SetLocalClearance(mm(0.3))
outline = zone.Outline()
outline.NewOutline()
for (x, y) in [(0.3, 0.3), (17.7, 0.3), (17.7, 23.2), (0.3, 23.2)]:
    outline.Append(pcbnew.VECTOR2I(mm(x), mm(y)))
board.Add(zone)

out = os.path.join(OUT, 'zero_board.kicad_pcb')
pcbnew.SaveBoard(out, board)
print('saved', out)

# ---------------- report: actual FFC pad geometry ----------------
b2 = pcbnew.LoadBoard(out)
for ref in ('J3', 'J4'):
    for fp in b2.GetFootprints():
        if str(fp.GetReference()) == ref:
            xs = {}
            for pad in fp.Pads():
                n = str(pad.GetNumber())
                if n.isdigit() and int(n) <= 30:
                    xs[int(n)] = (pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6)
            print(ref, 'pad1', xs[1], 'pad30', xs[30], 'layer', 'F' if fp.GetLayer() == 0 else 'B')
print('nets:', len(nets), 'footprints:', len(b2.GetFootprints()))
