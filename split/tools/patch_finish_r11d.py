#!/usr/bin/env python3
"""Hand-finish round 11d (redo_v11 board):
- EX5 v4: I2 ride east-shifted around GPIO15's via (6.6,20.61)
  and GPIO10's I2 diagonal end
- GPIO0 v4: F dive steep west to via (10.6,19.9), clear of
  GPIO11's I1 vertical x=10.91; I1 ride west onto (6.254,21.254)
- GPIO5 v4: F ride threaded south of U1.26 and under GPIO1's
  diagonal to via (10.7,18.05); B ride as v3
- GPIO6 v4: via (8.52,22.84), clear of GPIO4's B stub end and
  J1.16's rect corner; I2 ride onto (9.28,20.6)
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

try_chain('EX5r11d', [
    (S, 'EX5', I2, 6.95, 18.90, 7.30, 20.60),
    (S, 'EX5', I2, 7.30, 20.60, 8.90, 24.35),
    (S, 'EX5', I2, 8.90, 24.35, 10.90, 25.791),
])

try_chain('GPIO0r11d', [
    (S, 'GPIO0', F, 11.10, 22.075, 10.60, 19.90),
    (V, 'GPIO0', 10.60, 19.90),
    (S, 'GPIO0', I1, 10.60, 19.90, 6.254, 21.254),
])

try_chain('GPIO5r11d', [
    (S, 'GPIO5', F, 9.00, 17.3635, 9.42, 17.88),
    (S, 'GPIO5', F, 9.42, 17.88, 10.70, 18.05),
    (V, 'GPIO5', 10.70, 18.05),
    (S, 'GPIO5', B, 10.70, 18.05, 10.30, 19.90),
    (S, 'GPIO5', B, 10.30, 19.90, 9.35, 19.12),
])

try_chain('GPIO6r11d', [
    (S, 'GPIO6', B, 8.70, 22.75, 8.52, 22.84),
    (V, 'GPIO6', 8.52, 22.84),
    (S, 'GPIO6', I2, 8.52, 22.84, 9.28, 20.60),
])

pcbnew.SaveBoard(P, b)
print('saved')
