#!/usr/bin/env python3
"""Hand-finish for the 2026-11-12 redo route: close the 7 unconnected
pairs the router left, each candidate verified with checker.py before
it is added (sequentially, so earlier fixes become obstacles for
later ones). Prints PASS/FAIL per element; saves at the end.
Failed candidates are simply not added -- rerun after adjusting.
"""
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

# 1. STATUS_LED: F track end (5.0,17.3635) -> J2 pad30 (4.8,19.925)
add_via('STATUS_LED', 5.0, 17.3635)
add_seg('STATUS_LED', B, 5.0, 17.3635, 5.0, 19.6)
add_seg('STATUS_LED', B, 5.0, 19.6, 4.8, 19.925)

# 2. EX5: JP4 pad1 (10.9,26.6) F -> B track end (13.9,26.7733)
add_seg('EX5', F, 10.9, 26.6, 10.6, 25.8)
add_via('EX5', 10.6, 25.8)
add_seg('EX5', B, 10.6, 25.8, 13.9, 26.7733)

# 3. 3V3: trunk via (14.7,28.7) B -> SJ4 pad1 (14.7,30.6)
add_seg('3V3', B, 14.7, 28.7, 14.7, 30.6)

# 4. GPIO9: J1 stub end (8.4,19.25) -> J2 pad14 (9.6,19.925)
add_via('GPIO9', 8.4, 19.25)
add_seg('GPIO9', B, 8.4, 19.25, 9.6, 19.25)
add_seg('GPIO9', B, 9.6, 19.25, 9.6, 19.925)

# 5. GPIO11: J1 pad12 (7.8,19.925) F <-> J2 pad12 (10.2,19.925) B
add_seg('GPIO11', F, 7.8, 19.925, 7.8, 19.05)
add_via('GPIO11', 7.8, 19.05)
add_seg('GPIO11', B, 7.8, 19.05, 10.2, 19.05)
add_seg('GPIO11', B, 10.2, 19.05, 10.2, 19.925)

# 6. EX2: JP3 pad1 (12.3,23.8) F -> B track end (12.97,26.52)
add_seg('EX2', F, 12.3, 23.8, 12.3, 23.0)
add_via('EX2', 12.3, 23.0)
add_seg('EX2', B, 12.3, 23.0, 12.97, 26.52)

# 7. FFC2_3: SJ3 centre pad (13.0,30.6) B -> J4 pin3 (12.9,27.6)
add_seg('FFC2_3', B, 13.0, 30.6, 12.9, 27.6)

pcbnew.SaveBoard(P, b)
print('saved', P)
