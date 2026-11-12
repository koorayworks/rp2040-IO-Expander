#!/usr/bin/env python3
"""Hand-finish round 16b (redo_v16 board):
- GPIO3 v2: B stub end + via (7.9,19.35) (0.53 from GPIO13's
  via, 0.62 from GPIO9's), I2 ride to the web via (10.15,20.7);
  I1 variant if I2 blocked
- GPIO0 v2: via (6.8,22.4) west of GPIO4's B track end
  (7.0,22.75); I1 diagonal onto (11.6,20.85)
(GPIO4: fenced again -- GPIO5's router B vertical x=8.8 +
GPIO3's via; needs a placement via, round-17 seed)
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
            _, net, x, y = st[0], st[1], st[2], st[3]
            dia, drill = (st[4], st[5]) if len(st) > 4 else (0.45, 0.25)
            ok, clr, worst = check_via(b, net, x, y)
            print(('PASS' if ok else 'FAIL'), f'{name} via[{net}] ({x},{y}) clr={clr:.3f} {worst}')
            if not ok:
                ok_all = False; break
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetWidth(mm(dia)); v.SetDrill(mm(drill))
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

ok = try_chain('GPIO3r16b-I2', [
    (S, 'GPIO3', B, 7.80, 19.30, 7.90, 19.35),
    (V, 'GPIO3', 7.90, 19.35, 0.40, 0.20),
    (S, 'GPIO3', I2, 7.90, 19.35, 10.15, 20.70),
])
if not ok:
    try_chain('GPIO3r16b-I1', [
        (S, 'GPIO3', B, 7.80, 19.30, 7.90, 19.35),
        (V, 'GPIO3', 7.90, 19.35, 0.40, 0.20),
        (S, 'GPIO3', I1, 7.90, 19.35, 10.15, 20.70),
    ])

try_chain('GPIO0r16b', [
    (S, 'GPIO0', B, 6.90, 22.075, 6.80, 22.40),
    (V, 'GPIO0', 6.80, 22.40, 0.40, 0.20),
    (S, 'GPIO0', I1, 6.80, 22.40, 11.60, 20.85),
])

pcbnew.SaveBoard(P, b)
print('saved')
