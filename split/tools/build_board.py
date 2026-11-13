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
esd.SetPosition(pcbnew.VECTOR2I(mm(6.40), mm(8.00)))  # NOTE: with the library 1.32mm pads, pad6 sits 0.011mm from J2 shell pad S1 (4.68,5.82); pads are shrunk to 0.90mm below at build time (moving U1 broke routing completeness, 2026-11-11)
esd.SetOrientationDegrees(90)
board.Add(esd)
for p in esd.Pads():
    p.SetSize(pcbnew.VECTOR2I(mm(0.90), mm(0.60)))
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

# ---------------- FH35C connector (Plan D-kai, decided 2026-11-11) -------
# Hirose FH35C-31S-0.3SHW(50), LCSC C424662. Land pattern from the Hirose
# catalog (Recommended Land Dimensions): signal lands 0.23 x 0.70, two
# staggered rows 2.15 apart (matches the connector terminal datum).
# Front row (insertion side, 16 lands, span C=9.0) = odd contacts,
# back row (15 lands, span B=8.4) = even contacts. Contact m sits at
# x_local = -4.5 + 0.3*(m-1). Contacts 1..30 carry channels 1..30,
# contact 31 is NC. Fitting (tab) lands 0.6 x 0.9 at x_local = +/-5.1
# in the front-row band, tied to GND.
# Convention: contact 1 is at the LEFT when looking at the populated
# face with USB at the top and the opening facing down-board (+y).
# NOTE: pin-1 direction is by this convention from the catalog drawings;
# verify against the physical part at first article (a flip can be
# absorbed on the flex side without touching this board).
CONN_CX, CONN_CY = 9.0, 11.55
ROW_DY = 1.075  # half of the 2.15 row separation

def make_fh35c(reference, back):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID('split', 'FH35C-31S'))
    fp.SetReference(reference)
    fp.SetValue('FH35C-31S-0.3SHW')
    lay = lset(pcbnew.B_Cu, pcbnew.B_Mask, pcbnew.B_Paste) if back \
        else lset(pcbnew.F_Cu, pcbnew.F_Mask, pcbnew.F_Paste)

    def add_pad(num, xl, yl, w, h, netname):
        x = CONN_CX + xl
        if back:
            x = 18.0 - x
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(num))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetSize(pcbnew.VECTOR2I(mm(w), mm(h)))
        pad.SetPosition(pcbnew.VECTOR2I(mm(x), mm(CONN_CY + yl)))
        pad.SetLayerSet(lay)
        if netname:
            pad.SetNet(net(netname))
        fp.Add(pad)

    for m in range(1, 32):
        xl = -4.5 + 0.3 * (m - 1)
        yl = ROW_DY if m % 2 == 1 else -ROW_DY
        add_pad(m, xl, yl, 0.23, 0.70, CHANNELS[m - 1] if m <= 30 else None)
    add_pad(32, -5.1, ROW_DY, 0.6, 0.9, 'GND')
    add_pad(33, +5.1, ROW_DY, 0.6, 0.9, 'GND')

    silk = pcbnew.B_SilkS if back else pcbnew.F_SilkS
    def line(x1, y1, x2, y2, w=0.12):
        s = pcbnew.PCB_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        s.SetLayer(silk)
        s.SetWidth(mm(w))
        fp.Add(s)
    x0, x1 = CONN_CX - 5.7, CONN_CX + 5.7
    if back:
        x0, x1 = 18.0 - x1, 18.0 - x0
    y0, y1 = CONN_CY - 1.8, CONN_CY + 1.8
    line(x0, y0, x1, y0); line(x1, y0, x1, y1)
    line(x1, y1, x0, y1); line(x0, y1, x0, y0)
    # pin-1 dot at the front-left corner of the outline
    dotx = (18.0 - (CONN_CX - 5.35)) if back else (CONN_CX - 5.35)
    dot = pcbnew.PCB_SHAPE(fp)
    dot.SetShape(pcbnew.SHAPE_T_CIRCLE)
    dot.SetCenter(pcbnew.VECTOR2I(mm(dotx), mm(CONN_CY + 2.25)))
    dot.SetEnd(pcbnew.VECTOR2I(mm(dotx + 0.3), mm(CONN_CY + 2.25)))
    dot.SetLayer(silk)
    dot.SetWidth(mm(0.3))
    dot.SetFilled(True)
    fp.Add(dot)
    return fp

board.Add(make_fh35c('J3', back=False))
board.Add(make_fh35c('J4', back=True))
print('FH35C placed (front J3 / back J4)')

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
# WS2812B-2020 pinout (datasheet V1.3): 1=DO, 2=GND, 3=DI, 4=VDD.
# NOT the 5050 order (1=VDD, 2=DOUT, 3=GND, 4=DIN) -- the first routed
# board used the 5050 assignment and was fixed by hand 2026-11-13.
# BOM must specify WS2812B-2020-V6 (3.3-5.3V) for the 3.3V rail.
assign(led, '2', 'GND'); assign(led, '3', 'STATUS_LED'); assign(led, '4', '3V3')

cap = pcbnew.FootprintLoad(os.path.join(STD, 'Capacitor_SMD.pretty'), 'C_0402_1005Metric')
cap.SetFPID(pcbnew.LIB_ID('split', 'C_0402_1005Metric'))
cap.SetReference('C1')
cap.SetValue('100n')
cap.SetPosition(pcbnew.VECTOR2I(mm(11.75), mm(15.90)))
cap.SetOrientationDegrees(90)
board.Add(cap)
assign(cap, '1', '3V3'); assign(cap, '2', 'GND')

# ---------------- design rules for the autorouter ----------------
try:
    ncs = board.GetNetClasses()
    nc = ncs.FindNetClass('Default')
    if nc:
        nc.SetClearance(mm(0.10))
        nc.SetTrackWidth(mm(0.15))
        nc.SetViaDiameter(mm(0.45))
        nc.SetViaDrill(mm(0.25))
        print('netclass tuned: clearance 0.10 / track 0.15 / via 0.45/0.25')
except Exception as e:
    print('netclass tuning skipped:', e)

# ---------------- GND plane zone on In1 ----------------
# In1 only. A B.Cu zone in the DSN makes Freerouting treat B.Cu as a
# plane-only layer and J4's signal connections fail (fr10, 2026-11-11:
# 6 unrouted). The B.Cu GND zone is added post-route by
# patch_routed.py instead.
zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.In1_Cu)
zone.SetNet(net('GND'))
zone.SetLocalClearance(mm(0.3))
outline = zone.Outline()
outline.NewOutline()
for (x, y) in [(0.3, 0.3), (17.7, 0.3), (17.7, 23.2), (0.3, 23.2)]:
    outline.Append(pcbnew.VECTOR2I(mm(x), mm(y)))
board.Add(zone)

# ---------------- pre-routed stubs for the two hardest fanouts ----
# Freerouting (no-plane runs fr11/fr12) leaves exactly two links
# unrouted: USB_D- at J3-25 and STATUS_LED at D1-3 -- both pads sit in
# pockets whose fanout the router cannot start. Short F.Cu stubs
# (verified clear of all fr11 copper) give it reachable endpoints.
def stub(netname, x0, y0, x1, y1):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetWidth(mm(0.15))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net(netname))
    board.Add(t)

stub('USB_D-', 11.70, 12.97, 11.70, 13.60)      # J3-25 pad -> south
stub('STATUS_LED', 9.93, 16.38, 9.93, 17.30)    # D1-3 pad -> south
stub('GPIO14', 6.90, 12.97, 6.90, 13.60)        # J3-9 pad -> south (fr13
                                                # left this fanout open)

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
