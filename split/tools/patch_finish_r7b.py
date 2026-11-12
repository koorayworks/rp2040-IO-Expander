#!/usr/bin/env python3
"""Hand-finish round 7b (redo_v7 board): v2 chains after r7a blockers.
- EX2 tap: enter JP3 pad1's rect from the south-west inside the rect,
  staying clear of the PU_EX2 neck band
- EX5: via (7.00,17.45) north of the 3V3 I2 rail, I1 south run
- GPIO5: via (8.20,17.50) west, clear of GPIO1's seeded diagonal
- GPIO2: leg1 on I1, leg2 on B (I2 is walled by STATUS_LED's rail)
- GPIO6: via (9.30,15.15) north of TB1's I2 diagonal
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

try_chain('EX2tap7b', [
    (V, 'EX2', 12.40, 25.20),
    (S, 'EX2', B, 12.40, 25.20, 12.40, 26.775),
    (S, 'EX2', F, 12.40, 25.20, 12.40, 24.20),
    (S, 'EX2', F, 12.40, 24.20, 12.05, 24.22),
])

try_chain('EX5r7b', [
    (S, 'EX5', F, 7.00, 16.4635, 7.00, 17.45),
    (V, 'EX5', 7.00, 17.45),
    (S, 'EX5', I1, 7.00, 17.45, 10.90, 25.80),
    (V, 'EX5', 10.90, 25.80),
    (S, 'EX5', F, 10.90, 25.80, 10.90, 26.60),
    (S, 'EX5', F, 10.90, 26.60, 13.60, 26.90),
    (V, 'EX5', 13.60, 26.90),
    (S, 'EX5', B, 13.60, 26.90, 13.90, 27.60),
])

try_chain('GPIO5r7b', [
    (S, 'GPIO5', F, 9.00, 17.3635, 8.20, 17.50),
    (V, 'GPIO5', 8.20, 17.50),
    (S, 'GPIO5', I2, 8.20, 17.50, 9.60, 19.20),
    (V, 'GPIO5', 9.60, 19.20),
    (S, 'GPIO5', F, 9.60, 19.20, 9.60, 19.925),
    (S, 'GPIO5', B, 9.60, 19.20, 9.60, 20.60),
    (S, 'GPIO5', B, 9.60, 20.60, 8.40, 20.60),
    (S, 'GPIO5', B, 8.40, 20.60, 8.40, 19.925),
])

try_chain('GPIO2r7b', [
    (S, 'GPIO2', I1, 8.669, 14.379, 10.50, 21.30),
    (V, 'GPIO2', 10.50, 21.30),
    (S, 'GPIO2', F, 10.50, 21.30, 10.50, 22.075),
    (S, 'GPIO2', B, 8.669, 14.379, 7.50, 21.30),
    (V, 'GPIO2', 7.50, 21.30),
    (S, 'GPIO2', B, 7.50, 21.30, 7.50, 22.075),
])

try_chain('GPIO6r7b', [
    (S, 'GPIO6', F, 9.40, 16.4635, 9.30, 15.15),
    (V, 'GPIO6', 9.30, 15.15),
    (S, 'GPIO6', I1, 9.30, 15.15, 8.70, 22.75),
    (V, 'GPIO6', 8.70, 22.75),
    (S, 'GPIO6', F, 9.30, 22.075, 9.30, 22.75),
    (S, 'GPIO6', F, 9.30, 22.75, 8.70, 22.75),
])

pcbnew.SaveBoard(P, b)
print('saved')
