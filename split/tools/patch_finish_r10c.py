#!/usr/bin/env python3
"""Hand-finish round 10c (redo_v10 board; EX5 closed by r10a):
- GPIO1 v3: B ride west to via (6.5,18.55), F detour north around
  EX5's jog/via and GPIO13's stub start, onto the chain end
- GPIO3 v3: via (8.68,18.45) east of GPIO9's via, B jogs onto the
  J2 stub, I1 ride east into x=9.95 vertical
- GPIO6 v3: via (9.05,20.65), B north into the inter-row channel,
  west along y=21.4, dive into J2.17's rect (own pad); I1 from U1 via
- GPIO28 v3: I1 ride south-west to via (11.95,22.75), B east along
  y=22.75 south of the far-row rects, B north into J2.5
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

try_chain('GPIO1r10c', [
    (S, 'GPIO1', B, 7.20, 19.25, 6.50, 18.55),
    (V, 'GPIO1', 6.50, 18.55),
    (S, 'GPIO1', F, 6.50, 18.55, 6.90, 19.45),
    (S, 'GPIO1', F, 6.90, 19.45, 7.10, 18.35),
    (S, 'GPIO1', F, 7.10, 18.35, 7.40, 17.95),
])

try_chain('GPIO3r10c', [
    (V, 'GPIO3', 8.68, 18.45),
    (S, 'GPIO3', B, 8.68, 18.45, 8.35, 19.05),
    (S, 'GPIO3', B, 8.35, 19.05, 7.90, 19.35),
    (S, 'GPIO3', B, 7.90, 19.35, 7.80, 19.30),
    (S, 'GPIO3', I1, 8.68, 18.45, 9.95, 19.60),
])

try_chain('GPIO6r10c', [
    (S, 'GPIO6', F, 9.30, 22.075, 9.35, 21.30),
    (S, 'GPIO6', F, 9.35, 21.30, 9.05, 20.65),
    (V, 'GPIO6', 9.05, 20.65),
    (S, 'GPIO6', B, 9.05, 20.65, 9.05, 21.40),
    (S, 'GPIO6', B, 9.05, 21.40, 8.68, 21.40),
    (S, 'GPIO6', B, 8.68, 21.40, 8.70, 22.075),
    (S, 'GPIO6', I1, 9.40, 13.75, 9.05, 20.65),
])

try_chain('GPIO28r10c', [
    (S, 'GPIO28', I1, 12.5843, 22.0998, 11.95, 22.75),
    (V, 'GPIO28', 11.95, 22.75),
    (S, 'GPIO28', B, 11.95, 22.75, 12.30, 22.75),
    (S, 'GPIO28', B, 12.30, 22.75, 12.30, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
