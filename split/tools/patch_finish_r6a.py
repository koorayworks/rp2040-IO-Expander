#!/usr/bin/env python3
"""Hand-finish round 6a (redo_v6 board): FH35C island gaps.
GPIO0 J2 pad / GPIO2 J1 pad / GPIO3 J1 pad / GPIO13 stub /
GPIO14 J1 pad / GPIO8 three bare pads."""
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

try_chain('GPIO0r6', [
    (S, 'GPIO0', B, 6.90, 22.075, 6.90, 22.85),
    (S, 'GPIO0', B, 6.90, 22.85, 6.05, 23.50),
    (V, 'GPIO0', 6.05, 23.50),
    (S, 'GPIO0', I2, 6.05, 23.50, 6.105, 23.995),
])

try_chain('GPIO2r6', [
    (S, 'GPIO2', F, 10.50, 22.075, 10.95, 22.65),
    (V, 'GPIO2', 10.95, 22.65),
    (S, 'GPIO2', I1, 10.95, 22.65, 11.152, 22.909),
])

try_chain('GPIO3r6', [
    (S, 'GPIO3', F, 10.20, 19.925, 10.20, 19.20),
    (V, 'GPIO3', 10.20, 19.20),
    (S, 'GPIO3', I2, 10.20, 19.20, 9.85, 18.65),
    (V, 'GPIO3', 9.85, 18.65),
    (S, 'GPIO3', B, 9.85, 18.65, 7.80, 19.60),
])

try_chain('GPIO13r6', [
    (S, 'GPIO13', F, 7.20, 19.25, 7.55, 19.05),
    (V, 'GPIO13', 7.55, 19.05),
    (S, 'GPIO13', B, 7.55, 19.05, 10.669, 16.582),
])

try_chain('GPIO14r6', [
    (S, 'GPIO14', F, 6.90, 22.075, 6.90, 22.70),
    (V, 'GPIO14', 6.90, 22.70),
    (S, 'GPIO14', B, 6.90, 22.70, 10.90, 22.70),
    (S, 'GPIO14', B, 10.90, 22.70, 10.994, 21.442),
])

try_chain('GPIO8r6', [
    (S, 'GPIO8', F, 10.20, 16.4635, 10.15, 17.00),
    (S, 'GPIO8', F, 10.15, 17.00, 9.40, 17.00),
    (S, 'GPIO8', F, 9.40, 17.00, 9.05, 17.15),
    (V, 'GPIO8', 9.05, 17.15),
    (S, 'GPIO8', I1, 9.05, 17.15, 9.30, 22.75),
    (V, 'GPIO8', 9.30, 22.75),
    (S, 'GPIO8', B, 9.30, 22.75, 9.30, 22.075),
    (S, 'GPIO8', F, 8.70, 22.075, 8.70, 22.75),
    (S, 'GPIO8', F, 8.70, 22.75, 9.30, 22.75),
])

pcbnew.SaveBoard(P, b)
print('saved')
