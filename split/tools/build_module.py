#!/usr/bin/env python3
"""Build split/module_board/module_board.kicad_pcb (placement + nets, unrouted).

Module-side board of the split design (SPLIT_SPEC.md / split/MODULE_PINMAP.md,
frozen 2026-11-11): MDBT50Q-1MV2 only (no RP2040, owner decision), REV.B power
tree transplanted (TPS610994 boost + TPS2116 priority mux + TPS7A2033 LDO),
FH35C flex link to the Zero-side board, FFC#1 trackball + FFC#2 expansion,
JST PH battery, CAS-120A power switch, sensor power gate on TB1.

Redo of 2026-11-12 (owner decisions): the module-side copies of the
BOOT / RESET buttons and the status LED are GONE -- the back-flip flex
variant leaves the Zero-side buttons and LED uncovered, so the copies
only cost routing room. BOOT / RESET / STATUS_LED still arrive over
the flex channels. I2C pull-ups for FFC#1 (TB4/TB5) and FFC#2
(EX2/EX5) are fitted behind solder jumpers (see the pull-up section).

Frame: origin at board top-left corner (antenna end), x right, y down, mm.
Board: 18.0 x 36.0, 4 layers. Pad pinouts for U2/U3/U4/SW1/L1 and the FH12
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

# ---------------- buttons + LED: REMOVED (2026-11-12) ----------------
# The module-side BOOT/RESET buttons (SW1/SW2), the status LED (D1)
# and its decoupling cap (C9) were placed here in v1. Owner decision:
# with the back-flip flex variant the Zero-side buttons/LED are fully
# usable, so the copies are dropped. The BOOT / RESET / STATUS_LED
# nets remain -- they terminate at the module MCU and the flex pads.

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
make_sj('SJ3', 13.0, 30.6, 'FFC2_3', 'EX3', 'GND')
make_sj('SJ4', 15.6, 30.6, 'FFC2_4', 'EX4', '3V3')
make_sj('SJ6', 13.0, 32.6, 'FFC2_6', 'GND', 'EX6')
# NOTE (fixed 2026-11-12): SJ3/SJ4 originally had def/alt swapped --
# their power net is the TPS43 (alt) side, unlike SJ1/SJ6 where power
# is the default side. PINMAP_EXT.md's table is the spec: default =
# unified mode (pin3 = EX3, pin4 = EX4). SJ3's GND pad therefore sits
# on the EAST (alt) pad, and its GND stub/via moved to x 13.9 below.

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

# ---------------- I2C pull-ups (jumper-selectable, front) -------------
# Owner decision 2026-11-12: FFC#1 (TB4/TB5) and FFC#2 (EX2/EX5) get
# 4.7k pull-ups for I2C pointing devices (Cirque pads, Azoteq TPS43),
# each behind a 2-pad solder jumper so plain trackball (SPI) use
# carries no pull-up. FFC#1 defaults OFF (the trackball is its day
# job: pads only, bridge JP1/JP2 to enable). FFC#2 defaults ON
# (EX2/EX5 are SDA/SCL in both FFC#2 modes: a 0.20mm neck
# pre-connects, cut it to disable). The pull-up rail matches the
# port's sensor rail: 3V3_TB for FFC#1, plain 3V3 for FFC#2.
# Chain per pull-up: signal --[JP pads]-- PU_xx net --[4.7k]-- rail.
def make_pu_jumper(ref, cx, cy, sig_net, mid_net):
    # Hand-built 2-pad bridge, F.Cu, SJ pad geometry (0.7x0.9 at
    # 0.9 pitch). No SetLayer on the footprint: see the FH35C note.
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID('split', 'SJ-2P'))
    fp.SetReference(ref)
    fp.SetValue('PU-JP')
    for i, (dx, nn) in enumerate([(-0.45, sig_net), (0.45, mid_net)], start=1):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(i))
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetSize(pcbnew.VECTOR2I(mm(0.7), mm(0.9)))
        pad.SetPosition(pcbnew.VECTOR2I(mm(cx + dx), mm(cy)))
        pad.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.F_Mask))
        pad.SetNet(net(nn))
        fp.Add(pad)
    board.Add(fp)

def pullup(ref_r, ref_j, jx, jy, rx, sig_net, mid_net, rail_net):
    make_pu_jumper(ref_j, jx, jy, sig_net, mid_net)
    r = load('Resistor_SMD.pretty', 'R_0603_1608Metric', ref_r, '4.7k')
    place(r, rx, jy, 0)
    assign(r, '1', mid_net); assign(r, '2', rail_net)

pullup('R7', 'JP1', 4.35, 26.9, 6.8, 'TB4', 'PU_TB4', '3V3_TB')
pullup('R8', 'JP2', 4.35, 29.3, 6.8, 'TB5', 'PU_TB5', '3V3_TB')
pullup('R9', 'JP3', 12.75, 23.8, 15.4, 'EX2', 'PU_EX2', '3V3')
pullup('R10', 'JP4', 11.35, 26.6, 13.5, 'EX5', 'PU_EX5', '3V3')

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
stub(8.4, 19.925, 8.4, 18.98, F, 'GPIO9')    # J1 pad14 (extended north to the round-5 via)
stub(7.8, 19.925, 7.85, 21.15, F, 'GPIO11')  # J1 pad12 (round-5 pre-dive to its via)
stub(3.9, 22.075, 3.9, 22.75, B, 'GND')      # J2 tab 33
stub(14.1, 22.075, 14.1, 22.75, B, 'GND')    # J2 tab 32
stub(6.6, 19.925, 6.6, 19.15, B, 'GND')      # J2 pad24 (ch27 GND)
stub(6.6, 19.15, 6.0, 19.15, B, 'GND')       # -> GND via (moved west, see via list)
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
stub(6.21, 18.5, 6.21, 19.2, F, 'GND')       # J5 pad4, down to corridor
stub(12.9, 30.125, 12.9, 29.3, F, 'GND')     # C1 pad2
stub(11.8, 31.025, 10.2, 31.025, F, 'GND')   # C5 pad2 (joins C6 stub below)
stub(10.2, 31.025, 10.2, 31.925, F, 'GND')   # C5/C6 GND bridge
stub(10.2, 31.925, 8.9, 31.925, F, 'GND')    # C6 pad2 (under JST housing)
stub(16.3, 28.7375, 16.3, 29.75, F, 'GND')   # U2 pad2
stub(9.5, 30.6, 9.5, 32.3, B, '3V3')         # SJ1 default pad
stub(6.6, 19.925, 6.6, 19.4, F, 'GPIO15')   # J1 pad8 (GND via moved to (6.0,19.15))
stub(7.2, 19.925, 7.2, 19.25, F, 'GPIO13')   # J1 pad10
stub(10.8, 19.925, 10.8, 19.25, F, 'GPIO1')  # J1 pad22
stub(12.9, 22.075, 12.9, 22.75, B, '3V3')    # J2 pad3 (flex ch3, main 3V3 feed)
stub(10.5, 22.075, 10.5, 22.75, B, 'GPIO12') # J2 pad11
stub(8.7, 22.075, 8.7, 22.9, B, 'GPIO6')    # J2 pad17 (round 12: extended; tip via is in the round-12 block -- net_via is defined later)
stub(10.075, 24.9, 10.075, 26.5, F, '3V3')   # R6 pad1 (gate pull-up feed)
stub(13.9, 30.6, 13.9, 29.7, B, 'GND')       # SJ3 alt pad (TPS43 GND) -> via
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
    (6.0, 19.15),                    # J2 pad24 / J5 GND (was (6.6,19.25): 0.05mm from GPIO15 stub)
    (3.55, 6.4635), (3.55, 7.5635),  # U1 pin1 / pin2 stub ends
    (3.5, 17.3635),                  # U1 pin15 stub end
    (14.45, 6.4635),                 # U1 pin55 stub end
    (12.9, 29.3),                    # C1 pad2 stub end
    (8.9, 31.925),                   # C6/C5 stub end
    (16.3, 29.75),                   # U2 pad2 stub end
    (13.9, 29.7), (12.1, 33.5),      # SJ3 alt pad (GND) / SJ6 default pad
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
# U4 feed, the SJ1/Q1/R6 cluster, the FH35C feed and the module's
# VDD stub into a single node before routing starts. The x 7.7 column
# keeps 0.175mm from J6 pin1's PTH annulus on In2 (x 7.3 measured
# inside the ring). SWD pad1 (3V3 test pad) joins via a short F stub.
I2 = pcbnew.In2_Cu
stub(7.7, 25.85, 7.7, 34.45, I2, '3V3')          # main column
stub(7.7, 34.45, 7.4, 34.45, I2, '3V3')          # -> U4 via (jog west)
stub(7.7, 25.85, 8.3, 25.85, I2, '3V3')          # -> Q1 via
stub(7.7, 29.0, 12.3, 29.0, I2, '3V3')           # east rail (R6/SJ4)
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

# ---- I2C pull-up fixed links -------------------------------------------
# Jumper pad -> resistor pad on the same row (the PU_xx hop). For the
# FFC#2 pair a 0.20mm neck also pre-connects the signal pad to the
# pull-up (default ON, same pattern as the SJ necks: the neck carries
# the PU_xx net and touches the signal pad, so DRC shows one
# intentional shorting item per neck). FFC#1 stays open (default OFF).
stub(4.8, 26.9, 6.0, 26.9, F, 'PU_TB4')
stub(4.8, 29.3, 6.0, 29.3, F, 'PU_TB5')
stub(13.2, 23.8, 14.6, 23.8, F, 'PU_EX2')
stub(11.8, 26.6, 12.7, 26.6, F, 'PU_EX5')

def pu_neck(x1, x2, y, mid_net):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y)))
    t.SetWidth(mm(0.20))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net(mid_net))
    board.Add(t)

pu_neck(12.3, 13.2, 23.8, 'PU_EX2')
pu_neck(10.9, 11.8, 26.6, 'PU_EX5')

# ---- Round-5 fixed links (redo round-1 hand-finish findings) -----------
# Hand-finishing round 1 proved two FH35C escapes are boxed in at
# 0.15mm/0.099mm rules once every other net is routed:
# - GPIO9 (J1 pad14): the F stub is fenced by the GPIO3 pair, the
#   GPIO13 via+diag and the GPIO15 In2 rail; no via touching the stub
#   clears all four. Pre-drop a via at the stub's north end (B pad18
#   rect is 0.595mm away at placement) plus a short B lead, so the
#   router lands on B from the start.
# - GPIO11 (J1 pad12): no stub existed and its F escape crosses the
#   same cluster. Pre-dive it between the pad rows to a via with a
#   B lead into the row band.
net_via(8.4, 18.98, 'GPIO9')
stub(8.4, 18.98, 8.38, 18.85, B, 'GPIO9')  # round 22: tail
# swung W from (8.9,19.3); the E tail fenced GPIO5's J2 stub
# end (8.4,19.42) completely (see Round-22 block). Kept short:
# (8.15,18.6) grazed GPIO13's via (7.85,18.35)
net_via(7.85, 21.15, 'GPIO11')
stub(7.85, 21.15, 8.6, 21.45, B, 'GPIO11')

# ---- Round-6 fixed links (redo round-5 hand-finish findings) ---------
# Round 5 (redo_v5) routed everything except 7 pairs; hand-finishing
# closed the EX2/EX5 pull-up taps and the USB_D- A<->B hop, but three
# nets proved fully fenced at 0.15mm/0.099mm rules once the router's
# own copper was in place, so they get fixed seeds like round 5's:
# - GPIO10 (J1 pad13 <-> J2 pad13): full fixed bridge. F dives north
#   from the pad between the pad rows (the south stub stays as a
#   router doorway), via at (8.50,20.60) sits 0.10mm clear of the
#   pad14/pad18 rects on both faces, B lead lands inside J2 pad13's
#   rect. Router-independent: the two FH35C pads are tied before
#   routing starts.
# - GPIO1 (J1 pad22 <-> U1 pin20): the whole hand-found F path is
#   seeded (via-minefield bisector between the router's GPIO7/GPIO3
#   vias does not exist yet at placement, so the path is clear of
#   fixed copper; the router must simply respect it).
# - EX3 / EX4 (U1 pin50 / pin47): the router left both with zero
#   copper -- the east-edge escapes were blocked by its own EX1/EX2
#   tracks. Seed a short F escape + via each: EX3 west into the open
#   north area, EX4 east into the pin47/pin46 gap.
# - USB_D- (J2 pad25): the B pocket south of the pad got fenced by
#   the router's GPIO0 diagonal + GPIO28 via + J2 pad27 rect. Seed
#   the B south lead and a via at (6.30,22.85) (0.20mm clear of J1
#   pad7's rect on F) so the router starts from a firm node.
stub(8.1, 22.075, 8.5, 21.35, F, 'GPIO10')   # J1 pad13 -> north dive
stub(8.5, 21.35, 8.5, 20.6, F, 'GPIO10')
net_via(8.5, 20.6, 'GPIO10')
stub(8.5, 20.6, 9.9, 21.5, B, 'GPIO10')
stub(9.9, 21.5, 9.9, 22.1, B, 'GPIO10')      # into J2 pad13 rect
stub(10.8, 19.6, 10.65, 18.9, F, 'GPIO1')    # J1 pad22 stub -> NW
stub(10.65, 18.9, 10.43, 19.07, F, 'GPIO1')  # jog (via-minefield entry)
stub(10.43, 19.07, 9.89, 18.23, F, 'GPIO1')  # bisector run
stub(9.89, 18.23, 8.4, 17.95, F, 'GPIO1')
stub(8.4, 17.95, 7.4, 17.95, F, 'GPIO1')     # into U1 pin20 stub (y17.95:
# 17.80 measured 0.0615mm from U1 pad22 (GPIO3) -- south pad row rects
# end at y ~17.71, so the west run needs y >= ~17.93)
stub(12.75, 8.76, 11.5, 8.3, F, 'EX3')       # U1 pin50 escape west
net_via(11.5, 8.3, 'EX3')
stub(12.75, 10.36, 11.6, 11.05, F, 'EX4')    # U1 pin47 escape WEST:
# east is walled by pad46 (GPIO28) at (13.65,10.76) -- the east edge
# alternates pad columns x=12.75 / x=13.65, so the pin47/pin46 gap
# does not exist. Via clears TB6's rect (x <= 11.23) by 0.145mm.
net_via(11.6, 11.05, 'EX4')
stub(6.3, 22.075, 6.3, 22.85, B, 'USB_D-')   # J2 pad25 south lead
net_via(6.3, 22.85, 'USB_D-')

# ---- Round-7 fixed links (redo round-6 hand-finish findings) ---------
# Round 6 closed GPIO9/10/11/1 + USB_D- with the round-5/6 seeds, but
# three more nets proved fully fenced once router copper was in, and
# EX3/EX4's long runs never happened from one anchored end:
# - GPIO14 (J1 pad9): F fenced by the router's GPIO12 vertical +
#   GPIO2 via + J1 pad7 rect; B fenced by the near-row stub field.
#   Seed a north dive + via at placement (corridor is empty there).
# - GPIO13 (J1 pad10 stub end (7.20,19.25)): fenced by GPIO15's F
#   diagonal + GPIO1's via + GPIO3's B column + the far-row pad
#   rects. Seed a short F lead + via at (7.45,19.05).
# - GPIO8 (U1 pin27): no copper at all in round 6; F north slot is
#   fenced by GPIO7's track end + GPIO9's via, B by two diagonals
#   under the pad. Seed the north escape + via at (10.20,15.60).
# - EX3 / EX4: anchor the SJ end too (B lead + via), so the router
#   only has to meet in the middle instead of completing a ~20mm
#   run from the U1 escape alone.
stub(6.9, 22.075, 6.9, 21.3, F, 'GPIO14')    # J1 pad9 north dive
net_via(6.9, 21.3, 'GPIO14')
stub(7.2, 19.25, 7.85, 18.35, F, 'GPIO13')  # J1 pad10 stub -> via
net_via(7.85, 18.35, 'GPIO13')  # round 20: moved from (7.55,18.95)
# to open GPIO3's J2 stub-end fan (the old spot sat 0.43 from
# (7.8,19.3) and fenced every GPIO3 seed). West was blocked by
# EX5's via (6.95,18.9), east by GPIO1's F web (y=17.95 rail);
# (7.85,18.35) sits S of that rail (0.40) and 0.70 from GPIO3's
# new seed via (7.85,19.05)
stub(10.2, 16.4635, 10.2, 15.6, F, 'GPIO8') # U1 pin27 north escape
net_via(10.2, 15.6, 'GPIO8')
stub(10.2, 15.6, 11.12, 18.95, pcbnew.In1_Cu, 'GPIO8')  # round 10:
# seeded I1 lead south-east + anchor via; in round 9 the router
# never bridged the U1 island to either J pad
net_via(11.12, 18.95, 'GPIO8')
stub(12.1, 30.6, 11.85, 29.75, B, 'EX3')    # SJ3 west pad anchor
net_via(11.85, 29.75, 'EX3')  # (11.6,29.9 measured 0.125mm hole
# clearance from SJ1 pad3 -- moved SE)
stub(14.7, 30.6, 14.7, 29.7, B, 'EX4')      # SJ4 west pad anchor
net_via(14.7, 29.7, 'EX4')

# ---- Round-8 fixed links (redo round-7 hand-finish findings) ---------
# Round 7's router left EX2(tap)/EX5/GPIO5/GPIO6 bare and GPIO2's pads
# bare; eleven hand-finish iterations (r7a-r7k) showed each is fenced
# by router copper in ways that need placement-time anchors instead:
# - EX2 tap: every via spot near JP3 pad1 is fenced (RESET I1 diag,
#   GPIO12 I1 rail, GND B rail, 3V3 I2 vertical, TB1 via). Seed a
#   via at (12.00,24.20) inside pad1's west edge + short F lead.
# - EX5: U1 pin19's only exit is the x=7.00 slot under its own pad;
#   the F run south then needs a via west of GPIO15's F vertical and
#   clear of SWD pad4: seed via (6.80,19.65).
# - GPIO5: U1 pin24 is fenced by GPIO1's seeded diagonal (F),
#   STATUS_LED's I2 rail and GPIO13's I1 vertical. Seed the south
#   dive + via (9.00,18.30) on pin24's own column.
# - GPIO6: seed pin25's north escape via (9.40,13.75) (placement is
#   clear there; router vias blocked every hand attempt).
# - GPIO2: seed pin21's escape to the point the round-7 router
#   itself chose as its island end, via (8.669,14.379).
stub(12.3, 23.8, 11.92, 24.03, F, 'EX2')    # JP3 pad1 tap lead
net_via(11.92, 24.03, 'EX2')
stub(7.0, 16.4635, 7.0, 18.55, F, 'EX5')    # U1 pin19 south slot run
stub(7.0, 18.55, 6.95, 18.9, F, 'EX5')
net_via(6.95, 18.9, 'EX5')
stub(9.0, 17.3635, 9.0, 16.55, F, 'GPIO5')  # U1 pin24 north escape stub
stub(9.0, 16.55, 8.96, 15.82, F, 'GPIO5')   # round 14: tip via ride
stub(8.96, 15.82, 8.87, 15.36, F, 'GPIO5')
net_via(8.87, 15.36, 'GPIO5')
# (round 14: via at (8.87,15.36): 0.712 from GPIO3's tip via,
# 0.62 from GPIO4's new tip via (8.68,15.95), 0.33 west of
# pin25's rect; ride stays north of pin23's NE corner; the old
# note about GPIO1's diagonal owning (9.0,18.06) concerned the
# SOUTH side)
# and the row-A pad gap (0.40) cannot take a 0.45 via; the stub end
# at (9.0,16.55) gives the router an island north of the pad field.
stub(9.4, 16.4635, 9.4, 13.75, F, 'GPIO6')  # U1 pin25 north escape
net_via(9.4, 13.75, 'GPIO6')
stub(7.8, 16.4635, 7.7, 14.95, F, 'GPIO2')   # U1 pin21 escape (west jog,
stub(7.7, 14.95, 8.669, 14.379, F, 'GPIO2')  # round 10: the round-9
# diagonal fenced GPIO3's north escape completely; the jog hugs
# pin21's NW corner (0.18) and frees the x=8.2 column)
net_via(8.669, 14.379, 'GPIO2')

# ---- Round-9 fixed links (redo round-8 hand-finish findings) ---------
# Round 8 closed EX2/GPIO6 by seed and GPIO7/EX5 by hand, but six nets
# still failed: every via spot the hand-finish tried was fenced by
# round-8 router copper (USB_D+/- I1 diagonals, RESET I1 diagonal,
# GPIO0 I1/I2, GPIO5 I2, GPIO6 I1, 3V3 F). Seed them all instead:
# - GPIO3: no placement copper at all in round 8. North escape from
#   U1 pin22 (the row-A gap takes a via at (8.2,16.5), corner dist
#   0.331), a J1 pad20 dive via (10.35,20.85), and a plain J2 stub.
# - GPIO1: extend J2 pad22's B stub to a via (7.35,18.5) + F landing
#   on the seeded chain end (7.4,17.95).
# - GPIO5: extend J2 pad18 with B stubs to via (8.15,18.9).
# - GPIO4: J1 pad19 dive via (10.05,23.1).
# - GPIO26: J1 pad7 dive via (6.2,22.75).
# - GPIO2: J-side vias (10.5,21.3) F / (7.5,21.3) B + an I1 lead
#   east from the U1 island via.
# - GPIO7: via-in-pad at (9.0,19.925) joins J1.16 (F) and J2.16 (B)
#   directly (proved by hand in round 8, checker clr 0.124).
# - EX5: JP4 pad1 hop via (10.9,25.791) + F lead to the pad edge
#   (proved by hand in round 8).
stub(8.2, 17.3635, 8.2, 15.6, F, 'GPIO3')   # U1 pin22 north escape
net_via(8.2, 15.6, 'GPIO3')
# Round 10: with GPIO2's diagonal gone (west jog), the stub runs the
# full column to (8.2,15.6) and takes a via there (0.598 clear of
# pin23's NW corner). In round 9 the stub tip at (8.2,16.2) was
# fenced on every layer (diag N / pin23 E / pin21 W / chain S).
stub(10.2, 19.925, 10.15, 20.7, F, 'GPIO3')  # J1 pad20 dive
net_via(10.15, 20.7, 'GPIO3')
stub(7.8, 19.925, 7.8, 19.3, B, 'GPIO3')    # J2 pad20 stub
# GPIO1 J2: no via seed -- the pocket is fenced by EX5's via (6.95,18.9),
# GPIO13's via/stub and the 3V3 In2 rail (y=17.9); its B stub end
# (7.2,19.25) stays as the router's island end (bridged in rounds 5/7).
stub(8.4, 19.925, 8.4, 19.42, B, 'GPIO5')   # J2 pad18 stub (via fenced
# by GPIO9's via (8.4,18.98) + GPIO13's via + J2 pad20 rect: stub only)
stub(9.9, 22.075, 10.05, 22.9, F, 'GPIO4')  # J1 pad19 dive
net_via(10.05, 22.9, 'GPIO4')
stub(6.3, 22.075, 6.05, 22.5, F, 'GPIO26')  # J1 pad7 dive
stub(6.05, 22.5, 5.7, 22.75, F, 'GPIO26')
net_via(5.7, 22.75, 'GPIO26')
stub(10.5, 22.075, 10.5, 21.3, F, 'GPIO2')  # J1 pad21 dive
net_via(10.5, 21.3, 'GPIO2')
stub(7.5, 22.075, 7.45, 21.55, B, 'GPIO2')  # J2 pad21 dive
stub(7.45, 21.55, 7.35, 20.6, B, 'GPIO2')
net_via(7.35, 20.6, 'GPIO2')
stub(8.669, 14.379, 10.6, 14.6, pcbnew.In1_Cu, 'GPIO2')  # U1 island I1 lead
net_via(9.0, 19.925, 'GPIO7')               # via-in-pad J1.16/J2.16
stub(10.9, 25.791, 10.9, 26.15, F, 'EX5')   # JP4 pad1 hop
net_via(10.9, 25.791, 'EX5')

# ---- Round-11 fixed links (redo round-10 hand-finish findings) --------
# Round 10 closed GPIO4/GPIO8 by seed and EX5 by hand (4 elements),
# but five pairs still failed: on round-10 router copper every via
# spot for GPIO1-J2 / GPIO3-J2 / GPIO6-J1 / GPIO28-J2 was fenced, and
# the router left EX5's J4.5 pad with no copper at all. Seed anchors
# the router must respect instead (all clear placement copper):
# - GPIO1: B lead off the J2 stub end west to via (6.9,18.85) --
#   placement-clear of GPIO13's stub corner (0.50) and GND's B stubs.
# - GPIO3: B lead off the J2 stub end east to via (8.35,19.05).
# - GPIO6: F lead off J1 pad17 to via (9.5,21.5) (0.363 clear of
#   J1.19's rect, 0.446 of J2.16's far rect).
# - GPIO28: B lead off J2 pad5 south-west to via (11.9,22.6)
#   (0.471 clear of J1.27/J2.4's shared corner).
# - EX5: B lead off J4 pad5 north to via (13.88,25.74) (0.41 clear
#   of R10 pad2's rect corner -- the r10 hand-finish end point).
stub(7.2, 19.25, 7.2, 20.15, B, 'GPIO1')    # J2 stub extended south
# (ends at y=20.15: 0.474 clear of GPIO2's dive via (7.35,20.6))
# (every via anchor tried collides with another placement anchor:
# EX5 (6.95,18.9), GPIO13 (7.55,18.95), GPIO14 (6.9,21.3), GPIO2
# (7.35,20.6), GPIO11 (7.85,21.15), GPIO10 (8.5,20.6)+(8.5,21.35),
# U1 rects, the 3V3 I2 rail, on-stub = GPIO13's F stub endpoint.
# So: no via -- just extend the B stub south in its own column to
# (7.2,20.5) as a longer router island end; the router bridged
# this stub unaided in rounds 5/7)

# GPIO3 J2: NO anchor (round-11 conclusion). Every candidate was
# fenced by placement copper: GPIO13's via (7.55,18.95) + GPIO9's
# via (8.4,18.98) + GPIO5's B stub end (8.4,19.42) block all B
# leads off the stub; on-stub vias hit J1's F pads; the south
# column is fenced by GPIO2's via (7.35,20.6), GPIO11's via
# (7.85,21.15) and J1.12's rect. The plain stub stays the router's
# island end, as with GPIO1.
stub(9.3, 22.075, 9.35, 21.3, F, 'GPIO6')    # J1 pad17 dive
stub(9.35, 21.3, 9.28, 20.6, F, 'GPIO6')
# (via (9.5,21.5) sat on GPIO10's placement B diagonal
# (8.5,20.6)->(9.9,21.5); the west jog to (8.45,20.05) crossed
# GPIO10's via and GPIO9's F track. The anchor (9.28,20.6) is
# 0.422 clear of GPIO10's diagonal, 0.364 of J2.16's rect corner)
net_via(9.28, 20.6, 'GPIO6')
stub(12.3, 22.075, 12.1, 22.55, B, 'GPIO28')  # J2 pad5 south lead
stub(12.1, 22.55, 11.75, 22.85, B, 'GPIO28')
# (via (11.9,22.6) overlapped J1.25/J2.7's rects; the anchor
# (11.75,22.85) is 0.425 south of them)
net_via(11.75, 22.85, 'GPIO28')
stub(13.9, 27.6, 13.88, 25.74, B, 'EX5')    # J4 pad5 north lead
net_via(13.88, 25.74, 'EX5')

# ---- Round-13 fixed links -------------------------------------------
# Round 12 seeded all six round-11 stragglers and REGRESSED to 16
# pairs: the GPIO9 via move broke GPIO9, and EX5's long I2 ride
# fenced the west/south nets (GPIO8/GPIO14/USB_D-/GPIO28/GND).
# Round 13 = round-11 seeds + only the three small local anchors
# that round 12 proved out (GPIO0's dive fixed GPIO0's J1 side,
# GPIO6's tip via fixed GPIO6, GPIO5's tip via is free space):
# - GPIO0 J1: F dive east to via (11.6,20.85) (0.581 clear of
#   J1.24's SE corner in placement).
stub(11.1, 22.075, 11.6, 20.85, F, 'GPIO0')
net_via(11.6, 20.85, 'GPIO0')
# - GPIO6 J2: tip via for the extended stub (see the J2 pad17 stub).
net_via(8.7, 22.9, 'GPIO6')

# ---- Round-14 fixed links -------------------------------------------
# Round 13 (round-11 base + the 3 anchors above) scored best yet
# (847.67) with 5 pairs left: GPIO1, GPIO3 x2, GPIO4, USB_D+.
# Hand-finish in round-13 copper fenced all five. Round 14 adds:
# - GPIO4 U1: NO tip via -- the pocket north of U1's row A fits
#   only two vias (GPIO3's (8.2,15.6) + GPIO5's); every GPIO4 via
#   candidate lands <0.55 from one of them or from GPIO5's ride.
#   GPIO4 connected without one in rounds 10/11; round 13's bare
#   U1.23 was router variance.
# - USB_D+ J2: pad26 had NO placement stub at all (bare in r13).
#   B stub south + via (6.0,20.6), 0.325 clear of J2.27/J1.6 rects.
stub(6.0, 19.925, 6.0, 20.6, B, 'USB_D+')
net_via(6.0, 20.6, 'USB_D+')

# ---- Round-17 fixed links (0.40-via round) --------------------------
# Round 16 (0.40/0.20 vias allowed) left only 3 pairs -- GPIO0 J2,
# GPIO3 J2, GPIO4 U1 -- and hand-finish fenced all three on
# router copper. These placement vias (0.40 dia) claim the spots
# first so the router works around them:
def net_via40(x, y, net_name):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.40))
    v.SetDrill(mm(0.20))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net(net_name))
    board.Add(v)

# - GPIO4 U1: F escape + via (8.58,15.98): 0.537 from GPIO3's
#   tip via (8.2,15.6), 0.388 clear of GPIO5's tip ride
#   ((8.6,15.95) grazed the ride at 0.0916 clearance).
stub(8.6, 16.4635, 8.58, 15.98, F, 'GPIO4')
net_via40(8.58, 15.98, 'GPIO4')
# - GPIO0 J2: B ride west then north + via (6.8,20.65): the
#   y=21.3 band is full (GPIO14 (6.9,21.3) / GPIO11 (7.85,21.15))
#   and (7.3,20.9) hit GPIO2's via (7.35,20.6); the west jog
#   clears GPIO14's via by 0.409.
stub(6.9, 22.075, 6.3, 21.1, B, 'GPIO0')
net_via40(6.3, 21.1, 'GPIO0')  # round 27: via moved W
# from (6.8,20.65) -- it + USB_D+'s via caged GPIO15's
# pad completely; solver-verified pair with (6.7,20.75)
# - GPIO3 J2: with GPIO13's dive via moved W to (7.0,18.7)
#   (round 20), the stub-end fan opens: B lead + via40
#   (7.85,19.05): 0.525 clear of J1.12's rect, 0.554 from
#   GPIO9's via (8.4,18.98), 0.919 from GPIO13's via.
stub(7.8, 19.3, 7.85, 19.05, B, 'GPIO3')
net_via40(7.85, 19.05, 'GPIO3')

# ---- Round-21 fixed links (round-20 stragglers) -----------------------
# Round 20 closed GPIO3 (the seed above worked) but left USB_D-
# J1, GPIO5 (both J pads), EX5 J4 and GPIO4's U1-to-web gap;
# hand-finish on round-20 copper was fenced for all of them
# (patch_finish_r20a-d.py). Seed the fenced ends at placement:
# - USB_D- J1.25: F dive north into the inter-row band + via;
#   south dives are fenced by GPIO28's via (11.75,22.85), GND's
#   F vertical x=12.3 and J1.23's rect.
stub(11.7, 22.075, 12.2, 21.0, F, 'USB_D-')
net_via40(12.2, 21.0, 'USB_D-')  # (11.7,21.3) hit GPIO0's J1
# dive via (11.6,20.85) + its F diagonal; NE jog clears both
# - GPIO5 J1.18: F dive north + via (clears GPIO1's F web by
#   0.81); J2.18: B jog off the stub end + via (8.3,19.5),
#   0.529 from GPIO9's via (8.4,18.98).
stub(9.6, 19.925, 9.6, 19.0, F, 'GPIO5')
net_via40(9.6, 19.0, 'GPIO5')
# - GPIO5 J2: NO via seed -- the stub-end pocket is fully
#   fenced by GPIO3's B stub/via (W) and GPIO9's F stub/via
#   (E); (8.3,19.5) hit GPIO9's F stub, (7.95,19.5) hit
#   GPIO3's. The J1 seed + U1 anchor must carry it.
# - EX5 J4: the placement via (13.88,25.74) dead-ended on inner
#   layers in round 20 (3V3's I2 rail + GPIO14's via fence the
#   exits); anchor it north on I1.
stub(13.88, 25.74, 13.88, 24.3, pcbnew.In1_Cu, 'EX5')
# - GPIO4 U1: anchor the seed via (8.58,15.98) south-east on
#   both inner layers toward the web.
stub(8.58, 15.98, 9.8, 17.3, pcbnew.In1_Cu, 'GPIO4')
stub(8.58, 15.98, 9.8, 17.3, I2, 'GPIO4')

# ---- Round-22 fixed links (round-21 stragglers) -----------------------
# Round 21 closed USB_D-/EX5/GPIO4/GPIO3/GPIO0; GPIO2 and
# GPIO5 (x2) survived ten hand-finish scripts (r21a-j) -- their
# fields are via/track tiled on router copper. Placement help:
# - GPIO5 J2: with GPIO9's B tail swung W (above), the stub
#   end's NE fan opens: B lead + via40 (8.95,19.15), 0.576
#   from GPIO9's via (8.4,18.98).
stub(8.4, 19.42, 9.0, 19.2, B, 'GPIO5')
net_via40(9.0, 19.2, 'GPIO5')
# - GPIO5 U1: anchor the tip via (8.87,15.36) NW on I1 and
#   SE on I2 (the S field is fenced by GPIO3/GPIO4 copper).
stub(8.87, 15.36, 8.05, 14.35, pcbnew.In1_Cu, 'GPIO5')
stub(8.87, 15.36, 10.5, 17.3, I2, 'GPIO5')
# - GPIO2 U1: anchor the tip via (8.669,14.379) SE on I2
#   (its W field is via-tiled; the I1 anchor exists already).
stub(8.669, 14.379, 9.9, 16.1, I2, 'GPIO2')

# ---- Round-23 fixed links (round-22 stragglers) -----------------------
# Round 22 closed GPIO5/GPIO2; the last two pairs (GND's J2.2
# island, GPIO27's J1.6) survived hand-finish r22a (their
# pockets are router-via tiled). Seed both at placement:
# - GND J2.2: B lead off the stub end (13.2,19.25) + via.
stub(13.2, 19.25, 13.45, 19.25, B, 'GND')
net_via40(13.45, 19.25, 'GND')  # (13.05,19.35) shorted 3V3's
# I2 rail x=12.9 and grazed J1.30's rect
# - GPIO27 J1.6: F dive SOUTH-EAST into the inter-row band
#   (router copper fenced every N/E exit in round 22) + via;
#   USB_D+'s placement via (6.0,20.6) fences the straight S.
stub(6.0, 19.925, 5.05, 21.2, F, 'GPIO27')
net_via40(5.05, 21.2, 'GPIO27')  # long SW dive: USB_D+'s via
# (6.0,20.6) sits on the column and GPIO0's seeds tile the
# SE pocket; the SW ray clears USB_D+'s via by 0.403

# ---- Round-24 fixed links (GPIO7 straggler) ---------------------------
# Round 23 closed GND/GPIO27; GPIO7 (new break) survived
# patch_finish_r23a v1-v13: every layer's corridor between
# its U1 via (10.04,13.823) and the J dive via (9.0,19.925)
# is via/track tiled on router copper. Anchor both ends on
# In2 at placement and let the router close the middle.
net_via40(10.15, 13.75, 'GPIO7')  # round 30: nudged from
# (10.04,13.823) -- items saved at that exact point came
# back with GPIO2's net after SaveBoard (positional net
# flip in this KiCad build; verified by save+load tests)
stub(10.15, 13.75, 10.6, 15.0, I2, 'GPIO7')  # round 30:
# end pulled NE -- the (9.0,14.6) end sat 0.141 from
# GPIO2's I2 anchor and board load merged the two nets
# bent S -- the straight (8.6,13.9) run passed 0.107 from
# GPIO6's via (9.4,13.75) (a latent short the r30 DRC
# caught; earlier rounds' reports missed it)
stub(9.0, 19.925, 10.3, 19.2, I2, 'GPIO7')  # ENE fan: the
# straight N stub spears GPIO5's seed via (9.0,19.2), and
# the NE fan grazes its other via (9.6,19.0)

# ---- Round-26 fixed links (GPIO15 straggler) ---------------------------
# Round 25 closed GPIO7/GND; GPIO15 (new break) survived
# patch_finish_r25a v1-v14: J1.8's stub tip (6.6,19.4) sits
# in a four-disk trap (GND via W, J5.4 corner N, EX5 via NE,
# GPIO13 stub E) and every dive south threads USB_D+/GPIO0
# vias at exactly the floor. Seed a long SE dive at
# placement like GPIO27's SW dive.
# (the SE dive died on the far-row dive fan: GPIO13's stub,
# GPIO2's via, GPIO11's and GPIO10's dives tile y~21)
# Seed the U1 side instead: I2 anchor off the web's via.
net_via40(11.96, 13.158, 'GPIO15')  # round 30: this via
# was never actually in the script (the comment assumed a
# router via from r25); without it the anchor was a
# floating stub that DSN export drops
stub(11.96, 13.158, 10.55, 16.0, I2, 'GPIO15')
stub(10.55, 16.0, 10.75, 16.95, I2, 'GPIO15')
stub(10.75, 16.95, 7.0, 18.0, I2, 'GPIO15')  # waypoints
# dodge GPIO8's via (10.2,15.6) and GPIO2's anchor tip

# ---- Round-27 fixed links (GPIO15, J-side dive) -------------------------
# Rounds 25/26 + patch_finish_r25a (14 tries) and r26a (2)
# all failed: every F ray from the stub tip is disk-tiled.
# The one ray that clears EX5's via and GPIO13's stub end
# lands at (8.3,18.4); seed it as a placement dive.
stub(6.6, 19.925, 6.7, 20.75, F, 'GPIO15')
net_via40(6.7, 20.75, 'GPIO15')  # round 27: S dive --
# open once GPIO0's via moved W to (6.3,21.1); every
# other ray/landing in the pocket is disk-tiled

# ---- Round-28 fixed links (GPIO1/GPIO10/GPIO28) -------------------------
# Round 27 closed GPIO15/GPIO0 (the via-cage pair) but
# broke GPIO1, GPIO10, GPIO28. Seed all three.
stub(13.65, 14.764, 14.5, 15.2, F, 'GPIO10')
stub(14.5, 15.2, 14.35, 15.7, F, 'GPIO10')
net_via40(14.35, 15.7, 'GPIO10')
# (round 29: the I2 anchor segment is dropped -- in r28
# GPIO10 still broke with it and the run regressed to 9
# pairs; the via + F stub stay as the router's target)
stub(5.7, 22.075, 5.15, 22.8, F, 'GPIO28')
net_via40(5.15, 22.8, 'GPIO28')

# ---- Round-30 fixed links (r29 stragglers) ------------------------------
# GND J2.27, STATUS_LED J2.30, GPIO7 U1, GPIO11 J2.12,
# GPIO27 J2.6: give each bare stub a via + short lead.
# (round 30: GND J2.27 seed tried and dropped -- the SW
# B band is tiled by GPIO26's via (5.7,22.75), USB_D-'s
# lead/via (6.3,22.85) and J2.28/29 pads; GND closed in
# most rounds without a seed anyway)
# (round 30: STATUS_LED J2.30 seed tried at (4.8,18.6),
# (4.8,19.65), (5.45,19.3) -- all inside/grazing the
# J5/J1 pad rects or flipped on save; dropped, STATUS
# closed in most rounds unseeded)
# (round 30: no I1 anchor for GPIO7 -- every SW run from
# the via crosses GPIO2's I1 anchor (8.669,14.379)->
# (10.6,14.6); crossing same-layer tracks merge nets on
# board load, which is what flipped this seed to GPIO2)
stub(10.2, 19.25, 10.5, 18.45, B, 'GPIO11')
net_via40(10.5, 18.45, 'GPIO11')  # (10.35,18.6) flipped
# to GPIO1's net on save -- nudged
stub(12.0, 19.25, 11.85, 18.75, B, 'GPIO27')
net_via40(11.85, 18.75, 'GPIO27')  # (12.0,18.6) grazed
# 3V3's I2 run at y=18.3

# ---- Round-31 fixed links (GPIO1/GPIO9/USB_D+) ---------------------------
# (round 31: GPIO1 J2 seed abandoned after 6 candidate
# vias -- the pocket N of the far row is tiled by EX5's
# via/stub, GPIO13's via + I1 dive, GPIO3's via; GPIO1
# closes unseeded in ~half the rounds anyway)
stub(9.6, 19.925, 9.6, 19.45, B, 'GPIO9')
# round 32 final: base stub only. Every via/ride design
# for J2.14 died in the via tiling (GPIO5 (9.6,19.0)/
# (9.0,19.2), GPIO10 (8.5,20.6), GPIO11 (7.85,21.15),
# GPIO1's F wall); the stub at least hands the router a
# B-side start it never had.
# round 32: J2.14 had NO stub at all; the N pocket is
# walled by GPIO5's vias (9.6,19.0)/(9.0,19.2) + its B
# track -- go S around the row, via at (8.6,21.2), then
# I1 north into GPIO9's own via (8.4,18.98). The r31
# seed via (9.25,18.6) overlapped GPIO5's via copper
# and merged into GPIO5 on save.
stub(6.0, 20.6, 7.3, 19.9, I2, 'USB_D+')
# short NE anchor on I2 (the long I1 ride E along y~21
# is tiled by the J-side seed vias: GPIO15/GPIO14/GPIO11)
# ---- Round-33: USB_D+ south I2 anchor ----------------------------
# r30 post-mortem: the (6.0,20.6) via is imprisoned on
# routed boards (GPIO15/GPIO0/GPIO14/GPIO2 vias + I2
# fences). Give the router a pre-drawn I2 escape: SW
# then S along the board's south band to a via under
# the J1.26 approach.
stub(6.0, 20.6, 5.55, 22.2, I2, 'USB_D+')
stub(5.55, 22.2, 4.6, 22.5, I2, 'USB_D+')
stub(4.6, 22.5, 5.0, 23.9, I2, 'USB_D+')
stub(5.0, 23.9, 8.2, 23.95, I2, 'USB_D+')
# SW dip W of GPIO28's via (5.15,22.8); the GPIO26
# (5.7,22.75) / GPIO28 pair has no corridor between
stub(8.2, 23.95, 10.6, 23.5, I2, 'USB_D+')
stub(10.6, 23.5, 11.2, 22.95, I2, 'USB_D+')
net_via40(11.2, 22.95, 'USB_D+')
# end via S of the near-row pad band (band y 21.7-22.4
# is pad-dense at every 0.3 step)
# jogs clear USB_D-'s via (6.3,22.85) and GPIO4's
# vias (7.0,23.3) / (10.05,22.9)
# jogged S of GPIO4's via (7.0,23.3); end via at
# (11.3,22.6) -- (11.3,21.35) hit GPIO0's F track

# ---- Round-34 base stubs (chronic J2 pads had none) ----------------------
stub(10.8, 19.925, 10.8, 19.45, B, 'GPIO13')  # J2.10
stub(10.2, 19.925, 10.2, 19.25, B, 'GPIO11')  # J2.12: join
# the floating r30 seed stub at (10.2,19.25)
stub(11.1, 22.075, 11.1, 22.55, B, 'GPIO14')  # J2.9
stub(9.3, 22.075, 9.3, 22.55, B, 'GPIO8')     # J2.15

# ---- Round-35 inner targets ----------------------------------------------
# GPIO1 I1-target seed REVERTED: its via/stub died on
# GPIO13's via (7.85,18.35) + GPIO15's I1 vertical
# (x=7.41) -- the corridor is impassable at I1 too.
stub(8.4, 18.98, 8.9, 18.62, pcbnew.In1_Cu, 'GPIO9')
stub(8.9, 18.62, 9.3, 18.75, pcbnew.In1_Cu, 'GPIO9')
# bent N around GPIO5's via (9.0,19.2)
# GPIO9: extend its via's I1 reach E toward the J2
# stub tip (9.6,19.45).
