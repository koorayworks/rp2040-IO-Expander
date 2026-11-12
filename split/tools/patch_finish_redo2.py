#!/usr/bin/env python3
"""Hand-finish round 2 (seeded route): close the 7 remaining pairs.
Candidates derived from the round-2 track dump; every element is
checker-verified before being added (sequentially)."""
import os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker import check_seg, check_via

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
P = os.path.join(ROOT, 'split', 'module_board', 'module_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
mm = pcbnew.FromMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu

NETS = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname():
            NETS.setdefault(n.GetNetname(), n)

def add_seg(net, layer, x1, y1, x2, y2, w=0.15):
    ok, clr, worst = check_seg(b, net, layer, x1, y1, x2, y2, w)
    print(('PASS' if ok else 'FAIL'), f'seg[{net}] L{layer} ({x1},{y1})->({x2},{y2}) clr={clr:.3f} {worst}')
    if ok:
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(NETS[net])
        b.Add(t)
    return ok

def add_via(net, x, y):
    ok, clr, worst = check_via(b, net, x, y)
    print(('PASS' if ok else 'FAIL'), f'via[{net}] ({x},{y}) clr={clr:.3f} {worst}')
    if ok:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetWidth(mm(0.45)); v.SetDrill(mm(0.25))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(F, B); v.SetNet(NETS[net])
        b.Add(v)
    return ok

# 1. EX5: via beside JP4 pad1 touches pad (same net) + In1 track at y 26.91
add_via('EX5', 10.5, 26.91)

# 2. EX2: JP3 pad1 SW corner -> existing EX2 via (13.31,25.38)
add_seg('EX2', F, 12.0, 24.05, 13.31, 25.38)

# 3. 3V3 -> SJ4 pad1 north edge, jogging east of the FFC2_4 tracks
add_seg('3V3', B, 14.7, 28.7, 15.15, 29.1)
add_seg('3V3', B, 15.15, 29.1, 15.02, 29.75)
add_seg('3V3', B, 15.02, 29.75, 15.02, 30.15)

# 4. GPIO12: F stub end (7.5,22.75) -> via (10.5,22.9) -> B stub end
add_seg('GPIO12', F, 7.5, 22.75, 7.5, 23.25)
add_seg('GPIO12', F, 7.5, 23.25, 10.5, 23.25)
add_seg('GPIO12', F, 10.5, 23.25, 10.5, 22.9)
add_via('GPIO12', 10.5, 22.9)
add_seg('GPIO12', B, 10.5, 22.9, 10.5, 22.75)

# 5. GPIO6: J1 pad17 south, via east of J3 MP, B back to x 8.7 vertical
add_seg('GPIO6', F, 9.3, 22.075, 9.3, 23.6)
add_seg('GPIO6', F, 9.3, 23.6, 9.55, 23.6)
add_via('GPIO6', 9.55, 23.6)
add_seg('GPIO6', B, 9.55, 23.6, 9.55, 22.9)
add_seg('GPIO6', B, 9.55, 22.9, 8.7, 22.9)
add_seg('GPIO6', B, 8.7, 22.9, 8.7, 22.8)

# 6. GPIO8: J1 pad15 south + east, via (10.5,23.9), B around GPIO10 via
add_seg('GPIO8', F, 8.7, 22.075, 8.7, 23.9)
add_seg('GPIO8', F, 8.7, 23.9, 10.5, 23.9)
add_via('GPIO8', 10.5, 23.9)
add_seg('GPIO8', B, 10.5, 23.9, 10.5, 23.3)
add_seg('GPIO8', B, 10.5, 23.3, 9.5, 23.3)
add_seg('GPIO8', B, 9.5, 23.3, 9.5, 22.15)
add_seg('GPIO8', B, 9.5, 22.15, 9.3, 22.0)

# 7. GPIO15: F stub -> NW via (6.75,18.8) -> B run east at y 18.2
add_seg('GPIO15', F, 6.6, 19.7, 6.75, 19.2)
add_seg('GPIO15', F, 6.75, 19.2, 6.75, 18.8)
add_via('GPIO15', 6.75, 18.8)
add_seg('GPIO15', B, 6.75, 18.8, 6.75, 18.2)
add_seg('GPIO15', B, 6.75, 18.2, 11.84, 18.2)
add_seg('GPIO15', B, 11.84, 18.2, 11.84, 18.35)

pcbnew.SaveBoard(P, b)
print('saved', P)
