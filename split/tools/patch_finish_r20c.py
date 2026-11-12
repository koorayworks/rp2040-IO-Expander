#!/usr/bin/env python3
"""Hand-finish round 20c (redo_v20 board):
- GPIO4: I2 straight from the seed via (8.58,15.98) to the
  web's own via point (10.05,22.9) (I1 threading between
  GPIO10/GPIO7 vias is fenced)
- EX5: I1 straight (13.88,25.74)->(10.9,25.629) (3V3's I2 rail
  x=12.9 blocks the I2 jog)
- USB_D-: F hop west (11.7,22.075)->(11.15,22.5) + via + I1
  onto (11.7,24.379) [GND's F vertical x=12.3 blocks east hop]
- GPIO5a: (9.6,19.925)->(9.05,18.8)->(9.0,16.55)
- GPIO5b: B (8.4,19.42)->(8.95,18.7)->(9.6,19.2) + via + F
- GND: B (5.7,22.075)->(5.2,22.95) + via
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

try_chain('GPIO4r20c', [
    (S, 'GPIO4', I2, 8.58, 15.98, 10.05, 22.90),
])

try_chain('EX5r20c', [
    (S, 'EX5', I1, 13.88, 25.74, 10.90, 25.629),
])

try_chain('USBD-r20c', [
    (S, 'USB_D-', F, 11.70, 22.075, 11.15, 22.50),
    (V, 'USB_D-', 11.15, 22.50, 0.40, 0.20),
    (S, 'USB_D-', I1, 11.15, 22.50, 11.70, 24.379),
])

try_chain('GPIO5ar20c', [
    (S, 'GPIO5', F, 9.60, 19.925, 9.05, 18.80),
    (S, 'GPIO5', F, 9.05, 18.80, 9.00, 16.55),
])

try_chain('GPIO5br20c', [
    (S, 'GPIO5', B, 8.40, 19.42, 8.95, 18.70),
    (S, 'GPIO5', B, 8.95, 18.70, 9.60, 19.20),
    (V, 'GPIO5', 9.60, 19.20, 0.40, 0.20),
    (S, 'GPIO5', F, 9.60, 19.20, 9.60, 19.925),
])

try_chain('GNDr20c', [
    (S, 'GND', B, 5.70, 22.075, 5.20, 22.95),
    (V, 'GND', 5.20, 22.95, 0.40, 0.20),
])

pcbnew.SaveBoard(P, b)
print('saved')
