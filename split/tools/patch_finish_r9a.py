#!/usr/bin/env python3
"""Hand-finish round 9a (redo_v9 board): 3 nets left.
- GPIO3 bridge U1<->J2: F jog to via (8.6,15.6), I1 ride south-west,
  via (8.1,18.75), B hop onto the J2 stub
- GPIO8: I1 diagonal from the seed via (10.2,15.6) to via (9.3,21.3),
  B drop into J2.15, F jog into J1.15
- GPIO4: F jog to via (8.75,15.9), I2 ride south, via (8.75,22.6),
  B hop onto the J2 stub rail
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

try_chain('GPIO3r9a', [
    (S, 'GPIO3', F, 8.20, 16.20, 8.60, 15.60),
    (V, 'GPIO3', 8.60, 15.60),
    (S, 'GPIO3', I1, 8.60, 15.60, 8.10, 18.75),
    (V, 'GPIO3', 8.10, 18.75),
    (S, 'GPIO3', B, 8.10, 18.75, 7.80, 19.30),
])

try_chain('GPIO8r9a', [
    (S, 'GPIO8', I1, 10.20, 15.60, 9.30, 21.30),
    (V, 'GPIO8', 9.30, 21.30),
    (S, 'GPIO8', B, 9.30, 21.30, 9.30, 22.075),
    (S, 'GPIO8', F, 9.30, 21.30, 8.85, 21.60),
    (S, 'GPIO8', F, 8.85, 21.60, 8.70, 22.075),
])

try_chain('GPIO4r9a', [
    (S, 'GPIO4', F, 8.60, 16.4635, 8.75, 15.90),
    (V, 'GPIO4', 8.75, 15.90),
    (S, 'GPIO4', I2, 8.75, 15.90, 8.75, 22.60),
    (V, 'GPIO4', 8.75, 22.60),
    (S, 'GPIO4', B, 8.75, 22.60, 8.10, 22.75),
])

pcbnew.SaveBoard(P, b)
print('saved')
