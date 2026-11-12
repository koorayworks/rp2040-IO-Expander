#!/usr/bin/env python3
"""Hand-finish round 7h (redo_v7 board): v7 chains after r7g blockers.
- EX2 tap: via (13.20,25.20) -- TB1 via (13.31,25.10) found there;
  moved to (12.95,24.85), still clear of TB1's F endpoints
- GPIO5: via-in-gap (9.00,17.05) in the x=9.00 channel between rows
  (own pad24 below, gap between pin23/pin25 above), I1 south run
- GPIO6: I1 heads SSE first, east of GPIO8's seed via
- GPIO2: leg1 on I1 east of GPIO8's router via; leg2 on B from the
  leg1 via (B south from the island via is disk-fenced)
- EX5: via (6.15,19.95) west of GPIO15's F vertical
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

try_chain('EX2tap7h', [
    (V, 'EX2', 12.95, 24.85),
    (S, 'EX2', B, 12.95, 24.85, 13.30, 26.775),
    (S, 'EX2', F, 12.95, 24.85, 12.40, 24.20),
    (S, 'EX2', F, 12.40, 24.20, 12.05, 24.22),
])

try_chain('GPIO5r7h', [
    (S, 'GPIO5', F, 9.00, 17.3635, 9.00, 17.05),
    (V, 'GPIO5', 9.00, 17.05),
    (S, 'GPIO5', I1, 9.00, 17.05, 8.90, 18.60),
    (V, 'GPIO5', 8.90, 18.60),
    (S, 'GPIO5', F, 8.90, 18.60, 9.60, 19.925),
    (S, 'GPIO5', B, 8.90, 18.60, 8.40, 19.925),
])

try_chain('GPIO6r7h', [
    (S, 'GPIO6', F, 9.40, 16.4635, 9.40, 13.75),
    (V, 'GPIO6', 9.40, 13.75),
    (S, 'GPIO6', I1, 9.40, 13.75, 9.90, 16.35),
    (S, 'GPIO6', I1, 9.90, 16.35, 10.15, 19.30),
    (S, 'GPIO6', I1, 10.15, 19.30, 8.70, 22.75),
    (V, 'GPIO6', 8.70, 22.75),
    (S, 'GPIO6', F, 9.30, 22.075, 9.30, 22.75),
    (S, 'GPIO6', F, 9.30, 22.75, 8.70, 22.75),
])

try_chain('GPIO2r7h', [
    (S, 'GPIO2', I1, 8.669, 14.379, 10.55, 14.15),
    (S, 'GPIO2', I1, 10.55, 14.15, 10.50, 21.30),
    (V, 'GPIO2', 10.50, 21.30),
    (S, 'GPIO2', F, 10.50, 21.30, 10.50, 22.075),
    (S, 'GPIO2', B, 10.50, 21.30, 7.50, 21.30),
    (V, 'GPIO2', 7.50, 21.30),
    (S, 'GPIO2', B, 7.50, 21.30, 7.50, 22.075),
])

try_chain('EX5r7h', [
    (S, 'EX5', F, 7.00, 16.4635, 7.00, 19.10),
    (S, 'EX5', F, 7.00, 19.10, 6.35, 19.12),
    (S, 'EX5', F, 6.35, 19.12, 6.15, 19.95),
    (V, 'EX5', 6.15, 19.95),
    (S, 'EX5', I1, 6.15, 19.95, 8.75, 21.70),
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
