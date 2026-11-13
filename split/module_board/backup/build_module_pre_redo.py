#!/usr/bin/env python3
"""Build split/module_board/module_board.kicad_pcb (placement + nets, unrouted).

Module-side board of the split design (SPLIT_SPEC.md / split/MODULE_PINMAP.md,
frozen 2026-11-11): MDBT50Q-1MV2 only (no RP2040, owner decision), REV.B power
tree transplanted (TPS610994 boost + TPS2116 priority mux + TPS7A2033 LDO),
FH35C flex link to the Zero-side board, FFC#1 trackball + FFC#2 expansion,
JST PH battery, CAS-120A power switch, sensor power gate on TB1.

Frame: origin at board top-left corner (antenna end), x right, y down, mm.
Board: 18.0 x 34.0, 4 layers. Pad pinouts for U2/U3/U4/SW1/L1 and the FH12
were read off the proven REV.A / REV.B board files, not from memory.
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
OUT = os.path.join(ROOT, 'split', 'module_board')
os.makedirs(OUT, exist_ok=True)
mm = pcbnew.FromMM
STD = '/usr/share/kicad/footprints'
BW, BH = 18.0, 36.0   # spec target is 34, cap is 36: the bottom band
# (4x M2 holes + THT battery pins + boost/mux cluster) does not close
# at 34mm, so the board takes the full 36mm allowance.

def lset(*layers):
    s = pcbnew.LSET()
    for l in layers:
        s.AddLayer(l)
    return s

CHANNELS = [
    'VSYS', 'GND', '3V3', 'GPIO29', 'GPIO28', 'GPIO27', 'GPIO26', 'GPIO15',
    'GPIO14', 'GPIO13', 'GPIO12', 'GPIO11', 'GPIO10', 'GPIO9', 'GPIO8',
    'GPIO7', 'GPIO6', 'GPIO5', 'GPIO4', 'GPIO3', 'GPIO2', 'GPIO1', 'GPIO0',
    'GND', 'USB_D-', 'USB_D+', 'GND', 'BOOT', 'RESET', 'STATUS_LED',
]
assert len(CHANNELS) == 30

# MDBT50Q pin -> net (MODULE_PINMAP.md; None = NC, left unconnected)
MDBT = {
    1: 'GND', 2: 'GND', 3: None, 4: None, 5: None, 6: None, 7: None, 8: None,
    9: 'GPIO0', 10: 'EX6', 11: None, 12: 'VBAT', 13: None, 14: 'BOOT',
    15: 'GND', 16: 'STATUS_LED', 17: None, 18: None, 19: 'EX5', 20: 'GPIO1',
    21: 'GPIO2', 22: 'GPIO3', 23: 'GPIO4', 24: 'GPIO5', 25: 'GPIO6',
    26: 'GPIO7', 27: 'GPIO8', 28: '3V3', 29: 'GPIO9', 30: '3V3', 31: None,
    32: 'VSYS', 33: 'GND', 34: 'USB_D-', 35: 'USB_D+', 36: 'GPIO11',
    37: 'GPIO10', 38: 'GPIO13', 39: 'GPIO12', 40: 'RESET', 41: 'GPIO14',
    42: 'GPIO15', 43: 'GPIO27', 44: 'GPIO26', 45: 'GPIO29', 46: 'GPIO28',
    47: 'EX4', 48: 'EX1', 49: 'EX2', 50: 'EX3', 51: 'SWDIO', 52: None,
    53: 'SWDCLK', 54: None, 55: 'GND', 56: 'TB1', 57: 'TB2', 58: 'TB3',
    59: 'TB4', 60: 'TB5', 61: 'TB6',
}

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

ext = pcbnew.LoadBoard(os.path.join(ROOT, 'ext_board', 'ext_board.kicad_pcb'))
revb = pcbnew.LoadBoard(os.path.join(ROOT, 'ext_board_revb', 'ext_board_revb.kicad_pcb'))

def _clear_nets(fp):
    # A duplicated footprint keeps the SOURCE board's pad nets (REV.A's
    # GP17..GP25 etc.). Clear everything; callers assign what they mean.
    for pad in fp.Pads():
        pad.SetNetCode(0)
    return fp

def dup_ref(b, ref):
    for fp in b.GetFootprints():
        if fp.GetReference() == ref:
            return _clear_nets(fp.Duplicate())
    raise RuntimeError('ref not found: ' + ref)

def dup_match(b, match):
    for fp in b.GetFootprints():
        if match in str(fp.GetFPID().GetLibItemName()):
            return _clear_nets(fp.Duplicate())
    raise RuntimeError('fp not found: ' + match)

def load(libdir, name, ref, value=None):
    fp = pcbnew.FootprintLoad(os.path.join(STD, libdir), name)
    fp.SetReference(ref)
    if value:
        fp.SetValue(value)
    return fp

def place(fp, x, y, rot=0, back=False):
    # Flip() segfaults on a footprint that is not on a board yet
    # (place_ffc worked because it Adds first). So: Add, move, flip in
    # place around its own centre, then rotate. Flip toggles the side,
    # so apply it whenever the current side differs from the target
    # (duplicated footprints arrive on their source board's side:
    # REV.A's U2 is a back part, its buttons are front parts).
    board.Add(fp)
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    want = pcbnew.B_Cu if back else pcbnew.F_Cu
    if fp.GetLayer() != want:
        fp.Flip(pcbnew.VECTOR2I(mm(x), mm(y)), False)
    fp.SetOrientationDegrees(rot)
    return fp

# ---------------- outline ----------------
for (x1, y1, x2, y2) in [(0, 0, BW, 0), (BW, 0, BW, BH), (BW, BH, 0, BH), (0, BH, 0, 0)]:
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.05))
    board.Add(s)

# ---------------- screw holes (M2, four corners) ----------------
for i, (hx, hy) in enumerate([(2.5, 2.5), (15.5, 2.5), (2.5, 33.5), (15.5, 33.5)], start=1):
    h = load('MountingHole.pretty', 'MountingHole_2.2mm_M2', f'H{i}')
    place(h, hx, hy)

# ---------------- MDBT50Q (antenna toward the top edge) ----------------
u1 = dup_ref(ext, 'U1')
u1.SetReference('U1')
u1.SetOrientationDegrees(0)   # REV.A used rot 180 (antenna down); rot 0 puts it up
board.Add(u1)
u1.SetPosition(pcbnew.VECTOR2I(mm(9.0), mm(10.0)))
bb = u1.GetBoundingBox()
u1.SetPosition(pcbnew.VECTOR2I(mm(9.0), mm(10.0 + (0.15 - bb.GetY() / 1e6))))
for pin, nn in MDBT.items():
    if nn:
        assert assign(u1, pin, nn) >= 1, f'MDBT pin {pin}'
bb = u1.GetBoundingBox()
print('MDBT bbox after adjust:', [round(v / 1e6, 2) for v in (bb.GetX(), bb.GetY(), bb.GetWidth(), bb.GetHeight())])

# antenna keepout: no copper / tracks / vias under and ahead of the antenna
# (antenna = pad-free end of the can, top ~5mm of the module)
ko = pcbnew.ZONE(board)
ko.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu))
ko.SetIsRuleArea(True)
ko.SetDoNotAllowTracks(True)
ko.SetDoNotAllowVias(True)
ko.SetDoNotAllowCopperPour(True)
ko.SetDoNotAllowPads(False)   # the module's own corner pads sit at the boundary
ko.SetDoNotAllowFootprints(False)
o = ko.Outline()
o.NewOutline()
for (x, y) in [(2.8, 0.0), (15.2, 0.0), (15.2, 4.2), (2.8, 4.2)]:
    o.Append(pcbnew.VECTOR2I(mm(x), mm(y)))
board.Add(ko)

# ---------------- FH35C flex connector (same builder as Zero board) ----
CONN_CX, CONN_CY, ROW_DY = 9.0, 21.0, 1.075

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
            x = BW - x
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
    return fp

board.Add(make_fh35c('J1', back=False))
# NOTE: do NOT SetLayer(B_Cu) on the back FH35C (or on the SJ pads
# below). These hand-built footprints carry pads at absolute board
# coordinates with the footprint at the origin. Marking the footprint
# as a back component makes the Specctra exporter emit "back 180",
# and Freerouting then applies the back-side transform to the
# already-absolute pins, throwing them outside the board outline
# (module run frm1: all 33 J2 pins flagged, routing collapsed).
# The Zero board's J4 uses the un-marked construction and routes
# cleanly; the pads' own B.Cu layer set is what defines the copper.
board.Add(make_fh35c('J2', back=True))
print('FH35C placed (front J1 / back J2), centre y =', CONN_CY)

# ---------------- buttons + LED (front) ----------------
for ref, cx, cy, rot, sig in (('SW1', 4.6, 25.9, 0, 'BOOT'), ('SW2', 13.4, 26.0, 180, 'RESET')):
    sw = dup_match(ext, 'SW-SMD_4P')
    sw.SetReference(ref)
    place(sw, cx, cy, rot)
    a = assign(sw, '1', sig); b = assign(sw, '2', 'GND')
    print(ref, 'signal pads:', a, 'gnd pads:', b)

led = load('LED_SMD.pretty', 'LED_WS2812B-2020_PLCC4_2.0x2.0mm', 'D1', 'WS2812B-2020')
place(led, 16.25, 24.6, 0)
assign(led, '1', '3V3'); assign(led, '3', 'GND'); assign(led, '4', 'STATUS_LED')
c9 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C9', '100n')
place(c9, 11.9, 27.4, 90)
assign(c9, '1', '3V3'); assign(c9, '2', 'GND')

# ---------------- SWD pads (front, slot below the module) ----------------
swd = pcbnew.FOOTPRINT(board)
swd.SetFPID(pcbnew.LIB_ID('split', 'SWD-4P'))
swd.SetReference('J5')
swd.SetValue('SWD')
for i, (nn, px) in enumerate([('3V3', 2.4), ('SWDIO', 3.67), ('SWDCLK', 4.94), ('GND', 6.21)], start=1):
    pad = pcbnew.PAD(swd)
    pad.SetNumber(str(i))
    pad.SetShape(pcbnew.PAD_SHAPE_RECT)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetSize(pcbnew.VECTOR2I(mm(0.7), mm(1.4)))
    pad.SetPosition(pcbnew.VECTOR2I(mm(px), mm(18.5)))
    pad.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.F_Mask))
    pad.SetNet(net(nn))
    swd.Add(pad)
board.Add(swd)

# ---------------- battery connector JST PH (front) ----------------
# The SMD side-entry S2B-PH-SM4-TB pad field is 8.2 x 9.2mm -- too big for
# the bottom band. The THT top-entry B2B-PH-K has a ~5.8 x 3 pad field and
# its housing fits the band, so it wins on this board.
jbat = load('Connector_JST.pretty', 'JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical',
            'J6', 'B2B-PH-K')
place(jbat, 6.6, 31.6, 180)
assign(jbat, '1', 'BAT+'); assign(jbat, '2', 'GND'); assign(jbat, 'MP', 'GND')
for p in jbat.Pads():
    print('J6 pad', p.GetNumber(), p.GetNet().GetNetname(),
          round(p.GetPosition().x / 1e6, 2), round(p.GetPosition().y / 1e6, 2))

# ---------------- FFC#1 / FFC#2 (back, FH12-6S) ----------------
def place_ffc(ref, pad1_xy, netmap):
    fp = dup_ref(ext, 'J3')
    fp.SetReference(ref)
    board.Add(fp)
    assert fp.GetLayer() == pcbnew.B_Cu, 'REV.A J3 must already be a back footprint'
    p1 = None
    for pad in fp.Pads():
        if str(pad.GetNumber()) == '1':
            p1 = pad.GetPosition()
    dx = mm(pad1_xy[0]) - p1.x
    dy = mm(pad1_xy[1]) - p1.y
    fp.SetPosition(pcbnew.VECTOR2I(fp.GetPosition().x + dx, fp.GetPosition().y + dy))
    for pn, nn in netmap.items():
        assign(fp, pn, nn)
    bb = fp.GetBoundingBox()
    print(ref, 'bbox:', [round(v / 1e6, 2) for v in (bb.GetX(), bb.GetY(), bb.GetWidth(), bb.GetHeight())])
    return fp

place_ffc('J3', (3.9, 27.6),
          {'1': '3V3_TB', '2': 'TB2', '3': 'TB3', '4': 'TB4', '5': 'TB5', '6': 'GND', 'MP': 'GND'})
place_ffc('J4', (11.9, 27.6),
          {'1': 'FFC2_1', '2': 'EX2', '3': 'FFC2_3', '4': 'FFC2_4', '5': 'EX5', '6': 'FFC2_6', 'MP': 'GND'})

# ---------------- solder jumpers for FFC#2 (back) ----------------
def make_sj(ref, cx, cy, center_net, def_net, alt_net):
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID('split', 'SJ-3P'))
    fp.SetReference(ref)
    fp.SetValue('SJ')
    for i, (dx, nn) in enumerate([(-0.9, def_net), (0.0, center_net), (0.9, alt_net)], start=1):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(i))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetSize(pcbnew.VECTOR2I(mm(0.7), mm(0.9)))
        pad.SetPosition(pcbnew.VECTOR2I(mm(cx + dx), mm(cy)))
        pad.SetLayerSet(lset(pcbnew.B_Cu, pcbnew.B_Mask))
        pad.SetNet(net(nn))
        fp.Add(pad)
    # no SetLayer(B_Cu): see the FH35C note (Specctra back-transform)
    board.Add(fp)

make_sj('SJ1', 10.4, 30.6, 'FFC2_1', '3V3', 'EX1')
make_sj('SJ3', 13.0, 30.6, 'FFC2_3', 'GND', 'EX3')
make_sj('SJ4', 15.6, 30.6, 'FFC2_4', '3V3', 'EX4')
make_sj('SJ6', 13.0, 32.6, 'FFC2_6', 'GND', 'EX6')

# Default-mode neck traces (REV.A pattern): a 0.20mm neck joins each
# jumper's centre pad to its DEFAULT pad, so the board works as the
# unified mode out of the box. Switching = cut the neck, bridge the
# other side. The neck endpoints sit on the default net's pad, so the
# segment carries the centre net (FFC2_x) -- electrically the two pads
# become one node, which is exactly the default connection.
def sj_neck(cx, cy, center_net):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(cx - 0.9), mm(cy)))
    t.SetEnd(pcbnew.VECTOR2I(mm(cx), mm(cy)))
    t.SetWidth(mm(0.20))
    t.SetLayer(pcbnew.B_Cu)
    t.SetNet(net(center_net))
    board.Add(t)

sj_neck(10.4, 30.6, 'FFC2_1')
sj_neck(13.0, 30.6, 'FFC2_3')
sj_neck(15.6, 30.6, 'FFC2_4')
sj_neck(13.0, 32.6, 'FFC2_6')

# ---------------- power tree (back; footprints/nets from REV.B) ----------
u3 = dup_ref(revb, 'U3'); u3.SetReference('U3')
place(u3, 7.6, 29.6, 0, back=True)
for pn, nn in {'1': 'GND', '2': '3V3_BAT', '3': 'GND', '4': 'VBAT', '5': 'BOOST_SW', '6': 'VBAT', '7': 'GND'}.items():
    assign(u3, pn, nn)
l1 = dup_ref(revb, 'L1'); l1.SetReference('L1')
place(l1, 9.6, 34.2, 0, back=True)
assign(l1, '1', 'BOOST_SW'); assign(l1, '2', '3V3_BAT')
c4 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C4', '10u')
place(c4, 4.7, 29.5, 0, back=True)
assign(c4, '1', 'VBAT'); assign(c4, '2', 'GND')
# boost output cap lives on the front (back bottom band is saturated);
# the rail crosses faces on vias next to the cap.
c5 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C5', '10u')
place(c5, 11.8, 31.8, 90)
assign(c5, '1', '3V3_BAT'); assign(c5, '2', 'GND')

u4 = dup_ref(revb, 'U4'); u4.SetReference('U4')
place(u4, 5.6, 34.2, 0, back=True)
for pn, nn in {'1': 'GND', '2': '3V3', '3': '3V3_USB', '4': 'PR1', '5': '3V3_USB', '6': '3V3_BAT', '7': '3V3'}.items():
    assign(u4, pn, nn)
# PR1 divider on the front mid-left (the back bottom-left is inside
# the H3 hole exclusion + JST pin discs).
r4 = load('Resistor_SMD.pretty', 'R_0603_1608Metric', 'R4', '180k')
place(r4, 2.0, 24.6, 0)
assign(r4, '1', '3V3_USB'); assign(r4, '2', 'PR1')
r5 = load('Resistor_SMD.pretty', 'R_0603_1608Metric', 'R5', '100k')
place(r5, 2.0, 26.8, 0)
assign(r5, '1', 'PR1'); assign(r5, '2', 'GND')
c6 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C6', '100n')
place(c6, 10.2, 32.7, 90)
assign(c6, '1', '3V3_USB'); assign(c6, '2', 'GND')

# LDO group sits on the FRONT bottom band: the back bottom-right is
# unusable for >=4mm parts (H4 screw hole + SJ pads + FFC cable path).
u2 = dup_ref(ext, 'U2'); u2.SetReference('U2')
place(u2, 16.3, 27.6, 90)
for pn, nn in {'1': 'VSYS', '2': 'GND', '3': 'VSYS', '5': '3V3_USB'}.items():
    assign(u2, pn, nn)
c1 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C1', '10u')
place(c1, 12.9, 30.9, 90)
assign(c1, '1', 'VSYS'); assign(c1, '2', 'GND')
c2 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C2', '10u')
place(c2, 16.4, 31.6, 0)
assign(c2, '1', '3V3_USB'); assign(c2, '2', 'GND')

# Power switch: no hole-free 5x4.5mm zone exists in either bottom band
# (four M2 holes), so it goes on the back left edge beside the module,
# reachable from the board edge. Battery path crosses faces on vias.
swp = dup_ref(revb, 'SW1'); swp.SetReference('SW3')
place(swp, 2.05, 12.5, 0, back=True)
assign(swp, '1', 'BAT+'); assign(swp, '2', 'VBAT')

# sensor power gate: AO3401-class P-MOS (SOT-23: 1=G, 2=S, 3=D), TB1 active-low.
# Front mid band: the back mid band belongs to the FFC connectors.
q1 = load('Package_TO_SOT_SMD.pretty', 'SOT-23', 'Q1', 'AO3401')
place(q1, 7.6, 24.9, 0)
assign(q1, '1', 'TB1'); assign(q1, '2', '3V3'); assign(q1, '3', '3V3_TB')
rg = load('Resistor_SMD.pretty', 'R_0603_1608Metric', 'R6', '100k')
place(rg, 10.9, 24.9, 0)
assign(rg, '1', '3V3'); assign(rg, '2', 'TB1')

# MDBT decoupling (back, under the module)
c10 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C10', '10u')
place(c10, 5.2, 8.0, 90, back=True)
assign(c10, '1', '3V3'); assign(c10, '2', 'GND')
c11 = load('Capacitor_SMD.pretty', 'C_0603_1608Metric', 'C11', '100n')
place(c11, 5.2, 10.6, 90, back=True)
assign(c11, '1', '3V3'); assign(c11, '2', 'GND')

# ---------------- design rules + GND plane (same policy as Zero board) ---
try:
    ncs = board.GetNetClasses()
    nc = ncs.FindNetClass('Default')
    if nc:
        nc.SetClearance(mm(0.10)); nc.SetTrackWidth(mm(0.15))
        nc.SetViaDiameter(mm(0.45)); nc.SetViaDrill(mm(0.25))
        print('netclass tuned')
except Exception as e:
    print('netclass tuning skipped:', e)

zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.In1_Cu)
zone.SetNet(net('GND'))
zone.SetLocalClearance(mm(0.3))
outline = zone.Outline()
outline.NewOutline()
for (x, y) in [(0.3, 0.3), (17.7, 0.3), (17.7, 35.7), (0.3, 35.7)]:
    outline.Append(pcbnew.VECTOR2I(mm(x), mm(y)))
board.Add(zone)

# ---- Pre-route stubs -------------------------------------------------
# Round frm2 left 45 unconnected: the FH35C pad field, several module
# GND pads and scattered GND pads sit in pockets the router cannot
# enter. Short fixed stubs give it a doorway (same pattern as the
# Zero board's three stubs). Coordinates from the frm2 DRC report.
def stub(x1, y1, x2, y2, layer, net_name):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(0.15))
    t.SetLayer(layer)
    t.SetNet(net(net_name))
    board.Add(t)

F, B = pcbnew.F_Cu, pcbnew.B_Cu
# FH35C near row (y 22.075) escapes downward, far row (y 19.925) upward.
stub(3.9, 22.075, 3.9, 22.75, F, 'GND')      # J1 tab 32
stub(14.1, 22.075, 14.1, 22.75, F, 'GND')    # J1 tab 33
stub(12.3, 22.075, 12.3, 22.75, F, 'GND')    # J1 pad27 (ch24 GND)
stub(8.1, 22.075, 8.1, 22.75, F, 'GPIO10')   # J1 pad13
stub(7.5, 22.075, 7.5, 22.75, F, 'GPIO12')   # J1 pad11
stub(8.4, 19.925, 8.4, 19.25, F, 'GPIO9')    # J1 pad14
stub(3.9, 22.075, 3.9, 22.75, B, 'GND')      # J2 tab 33
stub(14.1, 22.075, 14.1, 22.75, B, 'GND')    # J2 tab 32
stub(6.6, 19.925, 6.6, 19.25, B, 'GND')      # J2 pad24 (ch27 GND)
stub(13.2, 19.925, 13.2, 19.25, B, 'GND')    # J2 pad2 (ch2 GND)
stub(8.1, 22.075, 8.1, 22.75, B, 'GPIO4')    # J2 pad19
stub(7.2, 19.925, 7.2, 19.25, B, 'GPIO1')    # J2 pad22
# Module pads.
stub(4.35, 6.4635, 3.55, 6.4635, F, 'GND')   # U1 pin1
stub(4.35, 7.5635, 3.55, 7.5635, F, 'GND')   # U1 pin2
stub(4.2, 17.3635, 3.5, 17.3635, F, 'GND')   # U1 pin15
stub(13.65, 6.4635, 14.45, 6.4635, F, 'GND') # U1 pin55
stub(7.4, 17.3635, 7.4, 18.1, F, 'GPIO1')    # U1 pin20 -> corridor
# Scattered GND / power pads.
stub(17.165, 25.15, 17.165, 25.45, F, 'GND')  # D1 pad3 (up would cross pad4/DIN)
stub(6.21, 18.5, 6.21, 19.2, F, 'GND')       # J5 pad4, down to corridor
stub(12.9, 30.125, 12.9, 29.3, F, 'GND')     # C1 pad2
stub(11.8, 31.025, 10.2, 31.025, F, 'GND')   # C5 pad2 (joins C6 stub below)
stub(10.2, 31.025, 10.2, 31.925, F, 'GND')   # C5/C6 GND bridge
stub(10.2, 31.925, 8.9, 31.925, F, 'GND')    # C6 pad2 (under JST housing)
stub(16.3, 28.7375, 16.3, 29.75, F, 'GND')   # U2 pad2
stub(11.9, 26.625, 11.0, 26.625, F, 'GND')   # C9 pad2
stub(4.6, 27.975, 3.3, 27.975, F, 'GND')     # SW1 pad2
stub(9.5, 30.6, 9.5, 32.3, B, '3V3')         # SJ1 default pad
stub(6.6, 19.925, 6.6, 19.6, F, 'GPIO15')   # J1 pad8 (short: GND via at (6.6,19.25))
stub(7.2, 19.925, 7.2, 19.25, F, 'GPIO13')   # J1 pad10
stub(10.8, 19.925, 10.8, 19.25, F, 'GPIO1')  # J1 pad22
stub(12.9, 22.075, 12.9, 22.75, B, '3V3')    # J2 pad3 (flex ch3, main 3V3 feed)
stub(10.5, 22.075, 10.5, 22.75, B, 'GPIO12') # J2 pad11
stub(8.7, 22.075, 8.7, 22.75, B, 'GPIO6')    # J2 pad17
stub(10.075, 24.9, 10.075, 26.5, F, '3V3')   # R6 pad1 (gate pull-up feed)
stub(11.9, 28.175, 11.9, 29.0, F, '3V3')     # C9 pad1
stub(11.9, 29.0, 11.55, 29.0, F, '3V3')      # C9 pad1 -> via point
stub(12.1, 30.6, 12.1, 29.7, B, 'GND')       # SJ3 default pad -> via
stub(12.1, 32.6, 12.1, 33.5, B, 'GND')       # SJ6 default pad -> via

# ---- Fixed GND vias to the In1 plane ---------------------------------
# Round frm3 showed GND keeps fragmenting into islands the router
# cannot unite. These pads get a via straight into the In1 GND pour,
# so they are connected no matter what the router does. Positions are
# the stub ends above, checked against the FH12 pad map (pins span
# y 26.95-28.25, MP pads y 23.25-25.45) and the FH35C pad edges.
def net_via(x, y, net_name):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.45))
    v.SetDrill(mm(0.25))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net(net_name))
    board.Add(v)

def gnd_via(x, y):
    net_via(x, y, 'GND')

for (vx, vy) in [
    (3.9, 22.75), (14.1, 22.75),      # FH35C tabs (serve J1 F + J2 B stubs)
    (6.6, 19.25),                    # J2 pad24 stub end (J5's stub hops 0.4mm to it)
    (3.55, 6.4635), (3.55, 7.5635),  # U1 pin1 / pin2 stub ends
    (3.5, 17.3635),                  # U1 pin15 stub end
    (14.45, 6.4635),                 # U1 pin55 stub end
    (17.165, 25.45),                 # D1 pad3 stub end (touches J4 MP: same net)
    (12.9, 29.3),                    # C1 pad2 stub end
    (11.0, 26.625),                  # C9 pad2 stub end
    (8.9, 31.925),                   # C6/C5 stub end
    (16.3, 29.75),                   # U2 pad2 stub end
    (3.3, 27.975),                   # SW1 pad2 stub end
    (12.1, 29.7), (12.1, 33.5),      # SJ3 / SJ6 default pads
]:
    gnd_via(vx, vy)

# ---- Round-4 fixed links (from the frm4 island map) -------------------
# GPIO4: the B stub is walled off by the FFC MP pads (GND, y 23.25-
# 25.45); the only B gap is x 2.9-7.4. Lead the stub west, then south
# through the gap, and drop a via there for the other layers.
stub(8.1, 22.75, 7.0, 22.75, B, 'GPIO4')
stub(7.0, 22.75, 7.0, 23.3, B, 'GPIO4')
net_via(7.0, 23.3, 'GPIO4')   # (23.55 would pierce Q1's gate pad on F)
# 3V3: give every frm4 island a fixed node on all layers.
stub(6.34, 34.45, 7.4, 34.45, B, '3V3')   # U4 VOUT pad7 -> trunk via
net_via(7.4, 34.45, '3V3')   # (7.7 would touch L1's BOOST_SW pad)
# SJ1 island: no via at the stub end (a via at (9.5,32.3) would sit
# 0.025mm from C6's GND pad on F). Instead the B stub runs west at
# y 32.52 into the trunk column (x 7.7). (y 32.45 measured 0.0911mm
# from J6 pin1's annulus -- 0.009 short of the 0.1 rule, hence 32.52.)
stub(9.5, 32.3, 9.5, 32.52, B, '3V3')
stub(9.5, 32.52, 7.7, 32.52, B, '3V3')
net_via(7.7, 32.52, '3V3')
net_via(11.55, 29.0, '3V3')               # C9 stub end
net_via(10.075, 26.5, '3V3')              # R6 stub end
stub(6.66, 25.85, 8.3, 25.85, F, '3V3')   # Q1 source pad -> via
net_via(8.3, 25.85, '3V3')
net_via(12.9, 22.75, '3V3')               # J2 pad3 stub end
# U1 VDD (pin28) + VDDH (pin30): join and stub south into the corridor.
stub(10.6, 17.3635, 11.4, 17.3635, F, '3V3')
stub(11.4, 17.3635, 11.4, 18.3, F, '3V3')
net_via(11.4, 18.3, '3V3')

# ---- 3V3 trunk on In2 --------------------------------------------------
# Rounds frm4/frm6 both left 3V3 in ~5 islands: the router links pads
# to the nearest fixed via but will not chain via-to-via. So chain
# them by hand on In2 (the emptiest layer): one fixed trunk ties the
# U4 feed, the SJ1/Q1/R6/C9 cluster, the FH35C feed and the module's
# VDD stub into a single node before routing starts. The x 7.7 column
# keeps 0.175mm from J6 pin1's PTH annulus on In2 (x 7.3 measured
# inside the ring). SWD pad1 (3V3 test pad) joins via a short F stub.
I2 = pcbnew.In2_Cu
stub(7.7, 25.85, 7.7, 34.45, I2, '3V3')          # main column
stub(7.7, 34.45, 7.4, 34.45, I2, '3V3')          # -> U4 via (jog west)
stub(7.7, 25.85, 8.3, 25.85, I2, '3V3')          # -> Q1 via
stub(7.7, 29.0, 12.3, 29.0, I2, '3V3')           # east rail (C9/R6)
stub(12.3, 29.0, 12.3, 28.55, I2, '3V3')         # dip under C1's GND via (12.9,29.3)
stub(12.3, 28.55, 14.7, 28.55, I2, '3V3')        # east rail cont. (SJ4)
stub(14.7, 28.55, 14.7, 28.7, I2, '3V3')
stub(10.075, 29.0, 10.075, 26.5, I2, '3V3')      # -> R6 via
stub(12.9, 28.55, 12.9, 18.3, I2, '3V3')         # north rail (J2 pad3 via)
stub(12.9, 18.3, 11.4, 18.3, I2, '3V3')          # -> U1 VDD stub via
stub(11.4, 18.3, 11.4, 17.9, I2, '3V3')
stub(11.4, 17.9, 1.9, 17.9, I2, '3V3')           # west rail (SWD feed)
net_via(14.7, 28.7, '3V3')                       # SJ4 hop point
net_via(1.9, 17.9, '3V3')
stub(1.9, 17.9, 2.4, 17.9, F, '3V3')
stub(2.4, 17.9, 2.4, 18.5, F, '3V3')             # -> SWD pad1

out = os.path.join(OUT, 'module_board.kicad_pcb')
pcbnew.SaveBoard(out, board)
print('saved', out)

# ---------------- report (pad extents; fp bbox is text-polluted) --------
def pad_extent(fp):
    xs, ys = [], []
    for p in fp.Pads():
        c, s = p.GetPosition(), p.GetSize()
        xs += [(c.x - s.x / 2) / 1e6, (c.x + s.x / 2) / 1e6]
        ys += [(c.y - s.y / 2) / 1e6, (c.y + s.y / 2) / 1e6]
    return (min(xs), max(xs), min(ys), max(ys)) if xs else (0, 0, 0, 0)

b2 = pcbnew.LoadBoard(out)
for fp in sorted(b2.GetFootprints(), key=lambda f: str(f.GetReference())):
    e = pad_extent(fp)
    flag = '  <-- OUT OF BOARD' if e[0] < -0.01 or e[1] > BW + 0.01 or e[2] < -0.01 or e[3] > BH + 0.01 else ''
    print(fp.GetReference(), fp.GetValue()[:22],
          'pads x %.2f..%.2f y %.2f..%.2f' % e,
          'layer', 'F' if fp.GetLayer() == 0 else 'B', flag)
for fp in b2.GetFootprints():
    if fp.GetReference() == 'U1':
        pos = {}
        for pn in ('1', '14', '15', '28', '34', '56'):
            for pad in fp.Pads():
                if str(pad.GetNumber()) == pn:
                    pos[pn] = (pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6)
                    print('U1 pad', pn, pad.GetNet().GetNetname(),
                          round(pos[pn][0], 2), round(pos[pn][1], 2))
        # antenna end is the pad-free end: in REV.A (antenna down) pad1 sat
        # at larger y than pad15. Here the antenna faces up, so pad1.y must
        # be SMALLER than pad15.y.
        print('antenna-up check (pad1.y < pad15.y):', pos['1'][1] < pos['15'][1])
print('nets:', len(nets), 'footprints:', len(b2.GetFootprints()))
