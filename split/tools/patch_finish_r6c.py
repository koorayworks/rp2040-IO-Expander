#!/usr/bin/env python3
"""Hand-finish round 6c (redo_v6 board): v3 chains after r6b blockers.
- GPIO0: x6.72 column between USB via and GPIO4 stub-end disks
- GPIO2: north exit from J1 pad21, via (10.85,21.35), I1 onto the
  router's I1 diagonal at (11.60,22.461)
- GPIO3: via1 (9.45,19.45) west of GPIO7 via, I2 jog, via2 (9.30,18.80)
- GPIO13: via west (7.10,18.55), B jog north across GPIO3's B column
- GPIO14: NE exit over J1 pad11 rect, via (8.00,21.15), I1, via
  (10.994,21.80) on its own J2 pad9
- GPIO8: pin27 escapes NW, via (9.85,15.75) clear of GPIO9's via
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

try_chain('GPIO0r6c', [
    (S, 'GPIO0', B, 6.90, 22.075, 6.72, 22.50),
    (S, 'GPIO0', B, 6.72, 22.50, 6.72, 22.95),
    (S, 'GPIO0', B, 6.72, 22.95, 6.30, 23.55),
    (V, 'GPIO0', 6.30, 23.55),
    (S, 'GPIO0', I2, 6.30, 23.55, 6.105, 23.995),
])

try_chain('GPIO2r6c', [
    (S, 'GPIO2', F, 10.50, 22.075, 10.85, 21.35),
    (V, 'GPIO2', 10.85, 21.35),
    (S, 'GPIO2', I1, 10.85, 21.35, 11.60, 22.461),
])

try_chain('GPIO3r6c', [
    (S, 'GPIO3', F, 10.20, 19.925, 10.20, 19.30),
    (S, 'GPIO3', F, 10.20, 19.30, 9.45, 19.45),
    (V, 'GPIO3', 9.45, 19.45),
    (S, 'GPIO3', I2, 9.45, 19.45, 9.30, 18.80),
    (V, 'GPIO3', 9.30, 18.80),
    (S, 'GPIO3', B, 9.30, 18.80, 7.80, 19.60),
])

try_chain('GPIO13r6c', [
    (S, 'GPIO13', F, 7.20, 19.25, 7.10, 18.55),
    (V, 'GPIO13', 7.10, 18.55),
    (S, 'GPIO13', B, 7.10, 18.55, 7.45, 17.45),
    (S, 'GPIO13', B, 7.45, 17.45, 10.669, 16.582),
])

try_chain('GPIO14r6c', [
    (S, 'GPIO14', F, 6.90, 22.075, 7.20, 21.475),
    (S, 'GPIO14', F, 7.20, 21.475, 8.00, 21.15),
    (V, 'GPIO14', 8.00, 21.15),
    (S, 'GPIO14', I1, 8.00, 21.15, 10.994, 21.80),
    (V, 'GPIO14', 10.994, 21.80),
])

try_chain('GPIO8r6c', [
    (S, 'GPIO8', F, 10.20, 16.4635, 9.85, 15.75),
    (V, 'GPIO8', 9.85, 15.75),
    (S, 'GPIO8', I1, 9.85, 15.75, 9.30, 22.75),
    (V, 'GPIO8', 9.30, 22.75),
    (S, 'GPIO8', B, 9.30, 22.75, 9.30, 22.075),
    (S, 'GPIO8', F, 8.70, 22.075, 8.70, 22.75),
    (S, 'GPIO8', F, 8.70, 22.75, 9.30, 22.75),
])

pcbnew.SaveBoard(P, b)
print('saved')
