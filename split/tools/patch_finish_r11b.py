#!/usr/bin/env python3
"""Hand-finish round 11b (redo_v11 board):
- EX5 v2: I2 ride jogged west of GPIO8's via (9.12,22.75)
- GPIO0 v2: F dive jogged west to via (10.85,21.25), clear of
  GPIO26's via (11.41,21.43); I1 ride west onto (6.254,21.254)
- GPIO5 v2: F tap jogged around GPIO1's diagonal to via
  (8.6,18.25) NE of GPIO3's I1 diagonal; B hop onto y=18.578
- GPIO6 v2: via (8.7,23.05) south of GPIO8's F stub end, I2 ride
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

try_chain('EX5r11b', [
    (S, 'EX5', I2, 6.95, 18.90, 8.60, 21.90),
    (S, 'EX5', I2, 8.60, 21.90, 8.90, 24.35),
    (S, 'EX5', I2, 8.90, 24.35, 10.90, 25.791),
])

try_chain('GPIO0r11b', [
    (S, 'GPIO0', F, 11.10, 22.075, 10.85, 21.25),
    (V, 'GPIO0', 10.85, 21.25),
    (S, 'GPIO0', I1, 10.85, 21.25, 6.254, 21.254),
])

try_chain('GPIO5r11b', [
    (S, 'GPIO5', F, 9.00, 17.3635, 8.85, 17.78),
    (S, 'GPIO5', F, 8.85, 17.78, 8.60, 18.25),
    (V, 'GPIO5', 8.60, 18.25),
    (S, 'GPIO5', B, 8.60, 18.25, 8.849, 18.578),
])

try_chain('GPIO6r11b', [
    (V, 'GPIO6', 8.70, 23.05),
    (S, 'GPIO6', I2, 8.70, 23.05, 9.28, 20.60),
])

pcbnew.SaveBoard(P, b)
print('saved')
