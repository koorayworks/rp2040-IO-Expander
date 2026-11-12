#!/usr/bin/env python3
"""Hand-finish round 6e (redo_v6 board): v5 chains after r6d blockers.
GPIO14 deferred: J1 pad9 is fully fenced on F in this routing
(GPIO12 vertical + GPIO2 via + pad7 rect) -- round-7 seed candidate.
- GPIO0: thread the USB-via/GPIO4-via gap point (6.64,23.08)
- GPIO2: east crossing over GPIO6's F rail, via (10.90,20.95)
- GPIO3: via1 (10.04,19.60) at its own J1 pad20 edge, I2 west
- GPIO13: dive south through its own pad10, via (7.05,19.95)
- GPIO8: via-in-pad moved to pin27 NW corner (9.99,16.25)
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

try_chain('GPIO0r6e', [
    (S, 'GPIO0', B, 6.90, 22.075, 6.72, 22.50),
    (S, 'GPIO0', B, 6.72, 22.50, 6.72, 22.95),
    (S, 'GPIO0', B, 6.72, 22.95, 6.64, 23.08),
    (S, 'GPIO0', B, 6.64, 23.08, 6.43, 23.29),
    (V, 'GPIO0', 6.43, 23.29),
    (S, 'GPIO0', I2, 6.43, 23.29, 6.105, 23.995),
])

try_chain('GPIO2r6e', [
    (S, 'GPIO2', F, 10.50, 22.075, 10.75, 21.85),
    (S, 'GPIO2', F, 10.75, 21.85, 10.90, 20.95),
    (V, 'GPIO2', 10.90, 20.95),
    (S, 'GPIO2', I1, 10.90, 20.95, 11.60, 22.461),
])

try_chain('GPIO3r6e', [
    (S, 'GPIO3', F, 10.20, 19.925, 10.20, 19.30),
    (S, 'GPIO3', F, 10.20, 19.30, 10.04, 19.60),
    (V, 'GPIO3', 10.04, 19.60),
    (S, 'GPIO3', I2, 10.04, 19.60, 9.35, 19.28),
    (V, 'GPIO3', 9.35, 19.28),
    (S, 'GPIO3', B, 9.35, 19.28, 7.80, 19.60),
])

try_chain('GPIO13r6e', [
    (S, 'GPIO13', F, 7.20, 19.25, 7.20, 19.90),
    (S, 'GPIO13', F, 7.20, 19.90, 7.05, 19.95),
    (V, 'GPIO13', 7.05, 19.95),
    (S, 'GPIO13', B, 7.05, 19.95, 8.30, 19.30),
    (S, 'GPIO13', B, 8.30, 19.30, 10.669, 16.582),
])

try_chain('GPIO8r6e', [
    (V, 'GPIO8', 9.99, 16.25),
    (S, 'GPIO8', I1, 9.99, 16.25, 9.30, 22.75),
    (V, 'GPIO8', 9.30, 22.75),
    (S, 'GPIO8', B, 9.30, 22.75, 9.30, 22.075),
    (S, 'GPIO8', F, 8.70, 22.075, 8.70, 22.75),
    (S, 'GPIO8', F, 8.70, 22.75, 9.30, 22.75),
])

pcbnew.SaveBoard(P, b)
print('saved')
