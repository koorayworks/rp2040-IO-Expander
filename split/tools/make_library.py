#!/usr/bin/env python3
"""Build the project-local footprint library split.pretty:
- USB-C TYPE-C-31-M-12 and tact switch extracted from Rev.W IO_BOARD (proven geometry)
- FH34SRJ-30S-0.5SH custom footprint (from Rev.N 24P geometry scaled to 30P;
  Hirose dims A=17.0 B=14.5 verified on the official product page 2026-11-10;
  tab positions extrapolated span/2+0.5 like the 24P part -- VERIFY against drawing before fab)
- ZeroEdge23: RP2040-Zero 23 edge pads from the official STEP extraction (2026-10-31)
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
LIB = os.path.join(ROOT, 'split', 'split.pretty')
os.makedirs(LIB, exist_ok=True)
mm = pcbnew.FromMM

def lset(*layers):
    s = pcbnew.LSET()
    for l in layers:
        s.AddLayer(l)
    return s

# ---------- extract proven footprints from IO_BOARD ----------
src = pcbnew.LoadBoard(os.path.join(ROOT, 'IO_BOARD.kicad_pcb'))
wanted = {}
for fp in src.GetFootprints():
    name = str(fp.GetFPID().GetLibItemName())
    if 'TYPE-C-31-M-12' in name:
        wanted['USB_C_TYPE-C-31-M-12'] = fp
    elif name.startswith('SW-SMD_4P'):
        wanted['SW_Tact_5.1x5.1'] = fp
for newname, fp in wanted.items():
    fp.SetFPID(pcbnew.LIB_ID('split', newname))
    pcbnew.FootprintSave(LIB, fp)
    print('saved extracted:', newname)

# ---------- FH34SRJ-30S-0.5SH ----------
fp = pcbnew.FOOTPRINT(None)
fp.SetFPID(pcbnew.LIB_ID('split', 'FH34SRJ-30S-0.5SH'))
# signal pads: 0.30 x 1.60, pitch 0.5, span 14.5 (pin k at x=(k-15.5)*0.5)
for k in range(1, 31):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(k))
    pad.SetShape(pcbnew.PAD_SHAPE_RECT)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetSize(pcbnew.VECTOR2I(mm(0.30), mm(1.60)))
    pad.SetPosition(pcbnew.VECTOR2I(mm((k - 15.5) * 0.5), 0))
    pad.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.F_Mask, pcbnew.F_Paste))
    fp.Add(pad)
# shell / mounting tabs at span/2 + 0.5 = +/-7.75, size 1.20 x 1.45 (24P pattern)
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

# body outline: 17.0 long; pad row near the cable mouth (+y side). Body y in [-2.45, +1.35] (depth 3.8)
for layer in (pcbnew.F_SilkS, pcbnew.F_Fab):
    line(layer, -8.5, -2.45, 8.5, -2.45)
    line(layer, 8.5, -2.45, 8.5, 1.35)
    line(layer, 8.5, 1.35, -8.5, 1.35)
    line(layer, -8.5, 1.35, -8.5, -2.45)
# pin-1 marker (dot) on silk near pad 1
c = pcbnew.PCB_SHAPE(fp)
c.SetShape(pcbnew.SHAPE_T_CIRCLE)
c.SetCenter(pcbnew.VECTOR2I(mm(-7.25), mm(-2.95)))
c.SetRadius(mm(0.35))
c.SetLayer(pcbnew.F_SilkS)
c.SetWidth(mm(0.12))
fp.Add(c)
# courtyard
for (x1, y1, x2, y2) in [(-8.7, -2.65, 8.7, -2.65), (8.7, -2.65, 8.7, 1.55), (8.7, 1.55, -8.7, 1.55), (-8.7, 1.55, -8.7, -2.65)]:
    line(pcbnew.F_CrtYd, x1, y1, x2, y2, 0.05)
t = pcbnew.PCB_TEXT(fp)
t.SetText('REF**')
t.SetPosition(pcbnew.VECTOR2I(mm(0), mm(-3.6)))
t.SetLayer(pcbnew.F_SilkS)
fp.Add(t)
pcbnew.FootprintSave(LIB, fp)
print('saved custom: FH34SRJ-30S-0.5SH')

# ---------- ZeroEdge23 ----------
# (net, hole_x, hole_y, inward dx, inward dy) -- STEP-verified hole centers
PADS = [
    ('VSYS', 1.38, 1.59), ('GND', 1.38, 4.13), ('3V3', 1.38, 6.67),
    ('GPIO29', 1.38, 9.21), ('GPIO28', 1.38, 11.75), ('GPIO27', 1.38, 14.29),
    ('GPIO26', 1.38, 16.83), ('GPIO15', 1.38, 19.37), ('GPIO14', 1.38, 21.92),
    ('GPIO13', 3.92, 21.92), ('GPIO12', 6.46, 21.92), ('GPIO11', 9.00, 21.92),
    ('GPIO10', 11.54, 21.92), ('GPIO9', 14.08, 21.92),
    ('GPIO8', 16.62, 21.92), ('GPIO7', 16.62, 19.37), ('GPIO6', 16.62, 16.83),
    ('GPIO5', 16.62, 14.29), ('GPIO4', 16.62, 11.75), ('GPIO3', 16.62, 9.21),
    ('GPIO2', 16.62, 6.67), ('GPIO1', 16.62, 4.13), ('GPIO0', 16.62, 1.59),
]
fp = pcbnew.FOOTPRINT(None)
fp.SetFPID(pcbnew.LIB_ID('split', 'ZeroEdge23'))
for i, (net, hx, hy) in enumerate(PADS, start=1):
    if hx < 9:      dx, dy, sx, sy = 0.30, 0.0, 2.4, 1.7    # left column, inward = +x
    elif hy > 21:   dx, dy, sx, sy = 0.0, -0.30, 1.7, 2.4   # bottom row, inward = -y
    else:           dx, dy, sx, sy = -0.30, 0.0, 2.4, 1.7   # right column, inward = -x
    if net in ('GPIO14',) and hy > 21:  # left-bottom corner belongs to left column geometry
        dx, dy, sx, sy = 0.30, 0.0, 2.4, 1.7
    if net in ('GPIO8',) and hy > 21:   # right-bottom corner: right column geometry
        dx, dy, sx, sy = -0.30, 0.0, 2.4, 1.7
    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(i))
    pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetSize(pcbnew.VECTOR2I(mm(sx), mm(sy)))
    pad.SetPosition(pcbnew.VECTOR2I(mm(hx + dx), mm(hy + dy)))
    pad.SetDrillSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
    pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_CIRCLE)
    # drill offset: hole must sit at the STEP position, pad center is offset inward
    pad.SetOffset(pcbnew.VECTOR2I(mm(-dx), mm(-dy)))
    pad.SetLayerSet(lset(pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask))
    fp.Add(pad)
pcbnew.FootprintSave(LIB, fp)
print('saved custom: ZeroEdge23')
print('library contents:', sorted(os.listdir(LIB)))
