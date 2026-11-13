#!/usr/bin/env python3
"""Round-40 experiment: graft ONLY the two proven seed
sets onto the r25 placement (which yielded exactly 1
unconnected pair, GPIO15):
  A) GPIO15: I2 anchor + start via (r26/r30) and the
     F S-dive + via (r27).
  B) USB_D+: J2 via (6.0,20.6) if missing, NE I2 anchor
     (r31) and the south I2 anchor + end via (r33).
Hypothesis: the full-seed placement (v31+) over-constrains
the router (rounds 37-39 gave 7/8/10 pairs); the leaner
r25 base + targeted fixes may reach 0-2.
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC = os.path.join(ROOT, 'split', 'module_board', 'backup',
                   'placement_v20_round25seeds.kicad_pcb')
OUT = os.path.join(ROOT, 'split', 'module_board',
                   'module_board.kicad_pcb')
b = pcbnew.LoadBoard(SRC)
mm = pcbnew.FromMM
F, B, I2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu

NETS = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname():
            NETS.setdefault(n.GetNetname(), n)

def stub(x1, y1, x2, y2, layer, net):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(0.15)); t.SetLayer(layer); t.SetNet(NETS[net])
    b.Add(t)

def via40(x, y, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.40)); v.SetDrill(mm(0.20))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F, B); v.SetNet(NETS[net])
    b.Add(v)

# --- inspect what v20 already has near the graft points
have_via = set()
for t in b.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        have_via.add((t.GetNetname(), round(pcbnew.ToMM(p.x), 2),
                      round(pcbnew.ToMM(p.y), 2)))
for probe in [('USB_D+', 6.0, 20.6), ('GPIO15', 11.96, 13.158),
              ('GPIO15', 6.7, 20.75)]:
    print('via', probe, 'present:', probe in have_via)

# --- A0) GPIO0 via move (r27 solver design): in v20 its
# J-side via sits at (6.8,20.65), exactly where GPIO15's
# dive needs to land. Replace it with the (6.3,21.1) via.
mmv = pcbnew.ToMM
for t in list(b.GetTracks()):
    if t.GetNetname() != 'GPIO0':
        continue
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        if abs(mmv(p.x) - 6.8) < 0.01 and abs(mmv(p.y) - 20.65) < 0.01:
            b.Remove(t); print('removed GPIO0 via (6.8,20.65)')
    else:
        s, e = t.GetStart(), t.GetEnd()
        pts = [(mmv(s.x), mmv(s.y)), (mmv(e.x), mmv(e.y))]
        if any(abs(px - 6.8) < 0.01 and abs(py - 20.65) < 0.01
               for px, py in pts):
            b.Remove(t); print('removed GPIO0 track touching old via', pts)
stub(6.9, 22.075, 6.3, 21.1, B, 'GPIO0')
via40(6.3, 21.1, 'GPIO0')

# --- A) GPIO15
via40(11.96, 13.158, 'GPIO15')
stub(11.96, 13.158, 10.55, 16.0, I2, 'GPIO15')
stub(10.55, 16.0, 10.75, 16.95, I2, 'GPIO15')
stub(10.75, 16.95, 7.0, 18.0, I2, 'GPIO15')
stub(6.6, 19.925, 6.7, 20.75, F, 'GPIO15')
via40(6.7, 20.75, 'GPIO15')

# --- B) USB_D+
if ('USB_D+', 6.0, 20.6) not in have_via:
    stub(6.0, 19.925, 6.0, 20.6, B, 'USB_D+')
    via40(6.0, 20.6, 'USB_D+')
stub(6.0, 20.6, 7.3, 19.9, I2, 'USB_D+')
stub(6.0, 20.6, 5.55, 22.2, I2, 'USB_D+')
stub(5.55, 22.2, 4.6, 22.5, I2, 'USB_D+')
stub(4.6, 22.5, 5.0, 23.9, I2, 'USB_D+')
stub(5.0, 23.9, 8.2, 23.95, I2, 'USB_D+')
stub(8.2, 23.95, 10.6, 23.5, I2, 'USB_D+')
stub(10.6, 23.5, 11.2, 22.95, I2, 'USB_D+')
via40(11.2, 22.95, 'USB_D+')

pcbnew.SaveBoard(OUT, b)
print('saved', OUT, 'tracks', len(list(b.GetTracks())))
