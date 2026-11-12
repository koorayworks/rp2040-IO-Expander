#!/usr/bin/env python3
"""Hand-finish round 8e (redo_v8 board, after r8a/b):
- GPIO3b v5: via (10.95,22.75), south of RESET's I1 rail
- GPIO4 v5: via (10.05,23.1), east of GPIO5's I2 rail end
- GPIO26 v5: via (5.35,23.05), I2 steep dive south of GPIO0's vertical
- GPIO2 v5: I1 far-east dive to (13.5,20.2), west to via (10.5,21.3)
(GPIO3a / GPIO1-J2 / GPIO5-J2 deferred to round-9 placement seeds.)
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

try_chain('GPIO3br8e', [
    (V, 'GPIO3', 10.95, 22.75),
    (S, 'GPIO3', F, 10.20, 19.925, 10.95, 22.75),
    (S, 'GPIO3', B, 10.95, 22.75, 10.60, 20.35),
    (S, 'GPIO3', B, 10.60, 20.35, 8.30, 19.05),
    (S, 'GPIO3', B, 8.30, 19.05, 7.966, 19.232),
])

try_chain('GPIO4r8e', [
    (V, 'GPIO4', 10.05, 23.10),
    (S, 'GPIO4', F, 9.90, 22.075, 10.05, 23.10),
    (S, 'GPIO4', B, 10.05, 23.10, 7.00, 23.30),
])

try_chain('GPIO26r8e', [
    (V, 'GPIO26', 5.35, 23.05),
    (S, 'GPIO26', F, 6.30, 22.075, 5.90, 22.60),
    (S, 'GPIO26', F, 5.90, 22.60, 5.35, 23.05),
    (S, 'GPIO26', I2, 5.35, 23.05, 6.10, 21.75),
    (S, 'GPIO26', I2, 6.10, 21.75, 9.30, 21.50),
    (S, 'GPIO26', I2, 9.30, 21.50, 11.435, 20.97),
])

try_chain('GPIO2r8e', [
    (S, 'GPIO2', I1, 8.669, 14.379, 13.50, 20.20),
    (S, 'GPIO2', I1, 13.50, 20.20, 10.50, 21.30),
    (V, 'GPIO2', 10.50, 21.30),
    (S, 'GPIO2', F, 10.50, 21.30, 10.50, 22.075),
    (S, 'GPIO2', B, 10.50, 21.30, 7.50, 21.30),
    (V, 'GPIO2', 7.50, 21.30),
    (S, 'GPIO2', B, 7.50, 21.30, 7.50, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
