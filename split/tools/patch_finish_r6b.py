#!/usr/bin/env python3
"""Hand-finish round 6b (redo_v6 board): v2 chains after r6a blockers.
- GPIO0: exit J2 pad23 at its SW corner, via (6.35,23.60)
- GPIO2: via moved to (10.85,22.70), clear of GPIO0's F vertical
- GPIO3: via1 west to (9.75,19.05), clear of GPIO11's B vertical
- GPIO13: via east to (8.00,18.60), clear of GPIO3 B column + GPIO9 via
- GPIO14: F east exit above GPIO12's track, via (7.85,22.35), I1 run,
  via (10.994,21.80) landing on its own J2 pad9 / B chain
- GPIO8: U1 pin27 escapes NORTH, via (10.20,15.60), I1 south run
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

try_chain('GPIO0r6b', [
    (S, 'GPIO0', B, 6.90, 22.075, 6.80, 22.45),
    (S, 'GPIO0', B, 6.80, 22.45, 6.60, 23.10),
    (S, 'GPIO0', B, 6.60, 23.10, 6.35, 23.60),
    (V, 'GPIO0', 6.35, 23.60),
    (S, 'GPIO0', I2, 6.35, 23.60, 6.105, 23.995),
])

try_chain('GPIO2r6b', [
    (S, 'GPIO2', F, 10.50, 22.075, 10.85, 22.70),
    (V, 'GPIO2', 10.85, 22.70),
    (S, 'GPIO2', I1, 10.85, 22.70, 11.152, 22.909),
])

try_chain('GPIO3r6b', [
    (S, 'GPIO3', F, 10.20, 19.925, 10.20, 19.30),
    (S, 'GPIO3', F, 10.20, 19.30, 9.75, 19.05),
    (V, 'GPIO3', 9.75, 19.05),
    (S, 'GPIO3', I2, 9.75, 19.05, 9.85, 18.65),
    (V, 'GPIO3', 9.85, 18.65),
    (S, 'GPIO3', B, 9.85, 18.65, 7.80, 19.60),
])

try_chain('GPIO13r6b', [
    (S, 'GPIO13', F, 7.20, 19.25, 8.00, 18.60),
    (V, 'GPIO13', 8.00, 18.60),
    (S, 'GPIO13', B, 8.00, 18.60, 10.669, 16.582),
])

try_chain('GPIO14r6b', [
    (S, 'GPIO14', F, 6.90, 22.075, 7.30, 22.35),
    (S, 'GPIO14', F, 7.30, 22.35, 7.85, 22.35),
    (V, 'GPIO14', 7.85, 22.35),
    (S, 'GPIO14', I1, 7.85, 22.35, 10.994, 21.80),
    (V, 'GPIO14', 10.994, 21.80),
])

try_chain('GPIO8r6b', [
    (S, 'GPIO8', F, 10.20, 16.4635, 10.20, 15.60),
    (V, 'GPIO8', 10.20, 15.60),
    (S, 'GPIO8', I1, 10.20, 15.60, 9.30, 22.75),
    (V, 'GPIO8', 9.30, 22.75),
    (S, 'GPIO8', B, 9.30, 22.75, 9.30, 22.075),
    (S, 'GPIO8', F, 8.70, 22.075, 8.70, 22.75),
    (S, 'GPIO8', F, 8.70, 22.75, 9.30, 22.75),
])

pcbnew.SaveBoard(P, b)
print('saved')
