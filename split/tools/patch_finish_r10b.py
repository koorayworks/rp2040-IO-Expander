#!/usr/bin/env python3
"""Hand-finish round 10b (redo_v10 board; EX5 closed by r10a):
- GPIO1: via (7.2,19.7) sitting on the J2 B stub, I1 ride north,
  via (7.4,17.95) landing on the seeded F stub
- GPIO3 v2: via (8.42,18.75) east of GPIO5's B track, B jog south
  then west onto the J2 stub, I1 ride east into x=9.95 vertical
- GPIO6 v2: F jog east then north-west to via (9.05,20.45) west of
  GPIO8's I2 vertical end; B ride onto J2.17's stub; I1 from the
  U1 via (9.4,13.75)
- GPIO28 v2: I1 extension to via (12.6,22.75) south of J2.4's rect,
  B west along y=22.75, B north into J2.5
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

try_chain('GPIO1r10b', [
    (V, 'GPIO1', 7.20, 19.70),
    (S, 'GPIO1', I1, 7.20, 19.70, 7.40, 17.95),
    (V, 'GPIO1', 7.40, 17.95),
])

try_chain('GPIO3r10b', [
    (V, 'GPIO3', 8.42, 18.75),
    (S, 'GPIO3', B, 8.42, 18.75, 8.30, 19.30),
    (S, 'GPIO3', B, 8.30, 19.30, 7.80, 19.30),
    (S, 'GPIO3', I1, 8.42, 18.75, 9.95, 19.60),
])

try_chain('GPIO6r10b', [
    (S, 'GPIO6', F, 9.30, 22.075, 9.35, 21.30),
    (S, 'GPIO6', F, 9.35, 21.30, 9.05, 20.45),
    (V, 'GPIO6', 9.05, 20.45),
    (S, 'GPIO6', B, 9.05, 20.45, 8.70, 22.075),
    (S, 'GPIO6', I1, 9.40, 13.75, 9.05, 20.45),
])

try_chain('GPIO28r10b', [
    (S, 'GPIO28', I1, 12.5843, 22.0998, 12.60, 22.75),
    (V, 'GPIO28', 12.60, 22.75),
    (S, 'GPIO28', B, 12.60, 22.75, 12.20, 22.75),
    (S, 'GPIO28', B, 12.20, 22.75, 12.30, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
