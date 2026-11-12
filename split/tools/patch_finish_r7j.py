#!/usr/bin/env python3
"""Hand-finish round 7j (redo_v7 board): v9 chains after r7i blockers.
- EX2 tap: via-in-pad on JP3 pad1 (12.00,24.20), B run to the chain
- GPIO5: F west along y~17.6-17.7, around GPIO1's corner spike,
  via (7.90,18.20)
- GPIO6: I1 seg1 ends (10.90,14.02) west of GPIO7's via (11.38,14.10)
- GPIO2: I1 two-step east, seg2 clear of BOOT's east horizontal end
- EX5: F swings east around GPIO15's F vertical end, via (6.30,20.45)
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

try_chain('EX2tap7j', [
    (V, 'EX2', 12.00, 24.20),
    (S, 'EX2', B, 12.00, 24.20, 12.40, 26.775),
])

try_chain('GPIO5r7j', [
    (S, 'GPIO5', F, 9.00, 17.3635, 8.80, 17.55),
    (S, 'GPIO5', F, 8.80, 17.55, 8.20, 17.65),
    (S, 'GPIO5', F, 8.20, 17.65, 7.90, 18.20),
    (V, 'GPIO5', 7.90, 18.20),
    (S, 'GPIO5', I1, 7.90, 18.20, 8.90, 18.60),
    (V, 'GPIO5', 8.90, 18.60),
    (S, 'GPIO5', F, 8.90, 18.60, 9.60, 19.925),
    (S, 'GPIO5', B, 8.90, 18.60, 8.40, 19.925),
])

try_chain('GPIO6r7j', [
    (S, 'GPIO6', F, 9.40, 16.4635, 9.40, 13.75),
    (V, 'GPIO6', 9.40, 13.75),
    (S, 'GPIO6', I1, 9.40, 13.75, 10.90, 14.02),
    (S, 'GPIO6', I1, 10.90, 14.02, 10.15, 19.30),
    (S, 'GPIO6', I1, 10.15, 19.30, 8.70, 22.75),
    (V, 'GPIO6', 8.70, 22.75),
    (S, 'GPIO6', F, 9.30, 22.075, 9.30, 22.75),
    (S, 'GPIO6', F, 9.30, 22.75, 8.70, 22.75),
])

try_chain('GPIO2r7j', [
    (S, 'GPIO2', I1, 8.669, 14.379, 11.20, 14.32),
    (S, 'GPIO2', I1, 11.20, 14.32, 10.50, 21.30),
    (V, 'GPIO2', 10.50, 21.30),
    (S, 'GPIO2', F, 10.50, 21.30, 10.50, 22.075),
    (S, 'GPIO2', B, 10.50, 21.30, 7.50, 21.30),
    (V, 'GPIO2', 7.50, 21.30),
    (S, 'GPIO2', B, 7.50, 21.30, 7.50, 22.075),
])

try_chain('EX5r7j', [
    (S, 'EX5', F, 7.00, 16.4635, 7.00, 19.10),
    (S, 'EX5', F, 7.00, 19.10, 6.70, 19.50),
    (S, 'EX5', F, 6.70, 19.50, 7.10, 20.50),
    (S, 'EX5', F, 7.10, 20.50, 6.30, 20.45),
    (V, 'EX5', 6.30, 20.45),
    (S, 'EX5', I1, 6.30, 20.45, 8.75, 21.70),
    (S, 'EX5', I1, 8.75, 21.70, 7.65, 24.00),
    (S, 'EX5', I1, 7.65, 24.00, 10.90, 25.80),
    (V, 'EX5', 10.90, 25.80),
    (S, 'EX5', F, 10.90, 25.80, 10.90, 26.60),
    (S, 'EX5', F, 10.90, 26.60, 13.60, 26.90),
    (V, 'EX5', 13.60, 26.90),
    (S, 'EX5', B, 13.60, 26.90, 13.90, 27.60),
])

pcbnew.SaveBoard(P, b)
print('saved')
