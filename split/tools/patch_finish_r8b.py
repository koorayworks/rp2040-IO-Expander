#!/usr/bin/env python3
"""Hand-finish round 8b (redo_v8 board, after r8a applied GPIO7):
- EX5: F seg ends at JP4 pad1 rect edge (26.15), not the centre --
  the PU_EX5 neck shares the centre point and the checker rejects it
- GPIO3a v2: via (8.2,18.75), south of GPIO13's I1 diagonal
- GPIO3b v2: via (10.6,21.1), B jog east of GPIO12's via, then west
- GPIO4 v2: via (9.3,23.65), south of GPIO5's I2 rail
- GPIO26 v2: via (6.3,22.0) overlapping J1.7's rect + I2 ride east
- GPIO2 v2: I1 seg1 ends (11.35,14.75), short of GPIO13's via
"""
import os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker import check_seg, check_via

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
P = os.path.join(ROOT, 'split', 'module_board', 'module_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
mm = pcbnew.FromMM
F, B, I1, I2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu

NETS = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname():
            NETS.setdefault(n.GetNetname(), n)

def try_chain(name, steps):
    added = []
    ok_all = True
    for st in steps:
        if st[0] == 'seg':
            _, net, layer, x1, y1, x2, y2 = st
            ok, clr, worst = check_seg(b, net, layer, x1, y1, x2, y2)
            print(('PASS' if ok else 'FAIL'), f'{name} seg[{net}] L{layer} ({x1},{y1})->({x2},{y2}) clr={clr:.3f} {worst}')
            if not ok:
                ok_all = False; break
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
            t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
            t.SetWidth(mm(0.15)); t.SetLayer(layer); t.SetNet(NETS[net])
            b.Add(t); added.append(t)
        else:
            _, net, x, y = st
            ok, clr, worst = check_via(b, net, x, y)
            print(('PASS' if ok else 'FAIL'), f'{name} via[{net}] ({x},{y}) clr={clr:.3f} {worst}')
            if not ok:
                ok_all = False; break
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetWidth(mm(0.45)); v.SetDrill(mm(0.25))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(F, B); v.SetNet(NETS[net])
            b.Add(v); added.append(v)
    if not ok_all:
        for it in added:
            b.Remove(it)
        print(f'  -> {name} ROLLED BACK ({len(added)} elements removed)')
    else:
        print(f'  -> {name} APPLIED ({len(added)} elements)')
    return ok_all

S = 'seg'; V = 'via'

try_chain('EX5r8b', [
    (V, 'EX5', 10.90, 25.791),
    (S, 'EX5', F, 10.90, 25.791, 10.90, 26.15),
])

try_chain('GPIO3ar8b', [
    (S, 'GPIO3', B, 7.966, 18.75, 8.20, 18.75),
    (V, 'GPIO3', 8.20, 18.75),
    (S, 'GPIO3', F, 8.20, 18.75, 8.20, 17.3635),
])

try_chain('GPIO3br8b', [
    (V, 'GPIO3', 10.60, 21.10),
    (S, 'GPIO3', F, 10.20, 19.925, 10.60, 21.10),
    (S, 'GPIO3', B, 10.60, 21.10, 10.62, 19.85),
    (S, 'GPIO3', B, 10.62, 19.85, 8.30, 19.05),
    (S, 'GPIO3', B, 8.30, 19.05, 7.966, 19.232),
])

try_chain('GPIO4r8b', [
    (V, 'GPIO4', 9.30, 23.65),
    (S, 'GPIO4', F, 9.90, 22.075, 9.30, 23.65),
    (S, 'GPIO4', B, 9.30, 23.65, 7.00, 23.30),
])

try_chain('GPIO26r8b', [
    (V, 'GPIO26', 6.30, 22.00),
    (S, 'GPIO26', I2, 6.30, 22.00, 11.435, 20.97),
])

try_chain('GPIO2r8b', [
    (S, 'GPIO2', I1, 8.669, 14.379, 11.35, 14.75),
    (S, 'GPIO2', I1, 11.35, 14.75, 10.50, 21.30),
    (V, 'GPIO2', 10.50, 21.30),
    (S, 'GPIO2', F, 10.50, 21.30, 10.50, 22.075),
    (S, 'GPIO2', B, 10.50, 21.30, 7.50, 21.30),
    (V, 'GPIO2', 7.50, 21.30),
    (S, 'GPIO2', B, 7.50, 21.30, 7.50, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
