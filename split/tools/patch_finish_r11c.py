#!/usr/bin/env python3
"""Hand-finish round 11c (redo_v11 board):
- EX5 v3: I2 ride west-dipped around GPIO10's I2 diagonal
- GPIO0 v3: F dive to via (10.88,20.9) between GPIO26's and
  GPIO2's vias; I1 ride west onto (6.254,21.254)
- GPIO5 v3: F ride east around GPIO1's diagonal end to via
  (10.45,18.45); B ride south then west into GPIO5's own via
  (9.25,18.979) disk, over GPIO6's B diagonal
- GPIO6 v3: B tap west to via (8.28,22.78); I2 ride onto (9.28,20.6)
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

try_chain('EX5r11c', [
    (S, 'EX5', I2, 6.95, 18.90, 6.60, 20.80),
    (S, 'EX5', I2, 6.60, 20.80, 8.90, 24.35),
    (S, 'EX5', I2, 8.90, 24.35, 10.90, 25.791),
])

try_chain('GPIO0r11c', [
    (S, 'GPIO0', F, 11.10, 22.075, 10.88, 20.90),
    (V, 'GPIO0', 10.88, 20.90),
    (S, 'GPIO0', I1, 10.88, 20.90, 6.254, 21.254),
])

try_chain('GPIO5r11c', [
    (S, 'GPIO5', F, 9.00, 17.3635, 9.70, 17.55),
    (S, 'GPIO5', F, 9.70, 17.55, 10.45, 18.45),
    (V, 'GPIO5', 10.45, 18.45),
    (S, 'GPIO5', B, 10.45, 18.45, 10.30, 19.90),
    (S, 'GPIO5', B, 10.30, 19.90, 9.35, 19.12),
])

try_chain('GPIO6r11c', [
    (S, 'GPIO6', B, 8.70, 22.75, 8.28, 22.78),
    (V, 'GPIO6', 8.28, 22.78),
    (S, 'GPIO6', I2, 8.28, 22.78, 9.28, 20.60),
])

pcbnew.SaveBoard(P, b)
print('saved')
