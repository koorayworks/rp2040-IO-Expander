#!/usr/bin/env python3
"""Hand-finish round 20d (redo_v20 board):
- GPIO4: I2 around STATUS_LED's y=17.49 rail end (12.5,17.49):
  (8.58,15.98)->(13.1,17.2)->(11.2,22.9)->(10.05,22.9)
- EX5: I1 jog north around GPIO14's via (11.85,25.68):
  (13.88,25.74)->(12.2,24.9)->(10.9,25.629)
- GPIO5b: B (8.4,19.42)->(8.75,19.0)->(9.6,19.2) + via + F
  vertical into J1.18 (its own pad)
- GND: B (5.7,22.075)->(5.05,23.1) + via
USB_D- J1.25 and GPIO5 J1.18 hand-finish are fenced on this
copper; they get placement seeds in round 21 instead.
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

try_chain('GPIO4r20d', [
    (S, 'GPIO4', I2, 8.58, 15.98, 13.10, 17.20),
    (S, 'GPIO4', I2, 13.10, 17.20, 11.20, 22.90),
    (S, 'GPIO4', I2, 11.20, 22.90, 10.05, 22.90),
])

try_chain('EX5r20d', [
    (S, 'EX5', I1, 13.88, 25.74, 12.20, 24.90),
    (S, 'EX5', I1, 12.20, 24.90, 10.90, 25.629),
])

try_chain('GPIO5br20d', [
    (S, 'GPIO5', B, 8.40, 19.42, 8.75, 19.00),
    (S, 'GPIO5', B, 8.75, 19.00, 9.60, 19.20),
    (V, 'GPIO5', 9.60, 19.20, 0.40, 0.20),
    (S, 'GPIO5', F, 9.60, 19.20, 9.60, 19.925),
])

try_chain('GNDr20d', [
    (S, 'GND', B, 5.70, 22.075, 5.05, 23.10),
    (V, 'GND', 5.05, 23.10, 0.40, 0.20),
])

pcbnew.SaveBoard(P, b)
print('saved')
