#!/usr/bin/env python3
"""Hand-finish round 10d (redo_v10 board; EX5 closed by r10a):
- GPIO3 v4: via (8.68,18.15) north of GPIO5's B horizontal, B jogs
  west staying north of it, then dives west of its west end
- GPIO6 v4: via (9.28,20.6) east of J2.16's near rect, clear of
  GPIO10's B diagonal; B jogs into the channel, west, dive
- GPIO28 v4: via (11.9,22.78) -- seg clears EX2's I1 jog by 0.252
(GPIO1's J2 stub is fenced on F/B/via spots in r10 copper:
deferred to a round-11 placement seed)
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

try_chain('GPIO3r10d', [
    (V, 'GPIO3', 8.68, 18.15),
    (S, 'GPIO3', B, 8.68, 18.15, 8.45, 18.28),
    (S, 'GPIO3', B, 8.45, 18.28, 8.02, 18.32),
    (S, 'GPIO3', B, 8.02, 18.32, 7.80, 19.30),
    (S, 'GPIO3', I1, 8.68, 18.15, 9.95, 19.60),
])

try_chain('GPIO6r10d', [
    (S, 'GPIO6', F, 9.30, 22.075, 9.35, 21.30),
    (S, 'GPIO6', F, 9.35, 21.30, 9.28, 20.60),
    (V, 'GPIO6', 9.28, 20.60),
    (S, 'GPIO6', B, 9.28, 20.60, 9.15, 21.35),
    (S, 'GPIO6', B, 9.15, 21.35, 8.68, 21.40),
    (S, 'GPIO6', B, 8.68, 21.40, 8.70, 22.075),
    (S, 'GPIO6', I1, 9.40, 13.75, 9.28, 20.60),
])

try_chain('GPIO28r10d', [
    (S, 'GPIO28', I1, 12.5843, 22.0998, 11.90, 22.78),
    (V, 'GPIO28', 11.90, 22.78),
    (S, 'GPIO28', B, 11.90, 22.78, 12.30, 22.78),
    (S, 'GPIO28', B, 12.30, 22.78, 12.30, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
