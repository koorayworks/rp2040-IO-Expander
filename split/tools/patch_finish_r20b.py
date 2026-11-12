#!/usr/bin/env python3
"""Hand-finish round 20b (redo_v20 board): jogged variants of r20a.
- GPIO4: I1 jog east around GPIO10's via (8.5,20.6):
  (8.58,15.98)->(8.92,18.0)->(8.92,23.306)
- EX5: I2 jog north around GPIO14's via (11.85,25.68):
  (13.88,25.74)->(12.2,24.9)->(10.9,25.629)
- USB_D-: F hop east (11.7,22.075)->(12.3,22.6) + via, I1 onto
  the web cluster (11.7,24.379) [GPIO28's via (11.75,22.85)
  blocks the straight dive]
- GPIO5a: F chain west-shifted around GPIO3's F diagonal:
  (9.6,19.925)->(9.05,18.75)->(9.0,16.55)
- GPIO5b: B two-seg south around GPIO9's B jog:
  (8.4,19.42)->(9.0,18.8)->(9.6,19.2) + via + F into J1.18
- GND: B lead west + via (5.15,22.7) [GPIO26's via (5.7,22.75)
  blocked the first spot]
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

try_chain('GPIO4r20b', [
    (S, 'GPIO4', I1, 8.58, 15.98, 8.92, 18.00),
    (S, 'GPIO4', I1, 8.92, 18.00, 8.92, 23.306),
])

try_chain('EX5r20b', [
    (S, 'EX5', I2, 13.88, 25.74, 12.20, 24.90),
    (S, 'EX5', I2, 12.20, 24.90, 10.90, 25.629),
])

try_chain('USBD-r20b', [
    (S, 'USB_D-', F, 11.70, 22.075, 12.30, 22.60),
    (V, 'USB_D-', 12.30, 22.60, 0.40, 0.20),
    (S, 'USB_D-', I1, 12.30, 22.60, 11.70, 24.379),
])

try_chain('GPIO5ar20b', [
    (S, 'GPIO5', F, 9.60, 19.925, 9.05, 18.75),
    (S, 'GPIO5', F, 9.05, 18.75, 9.00, 16.55),
])

try_chain('GPIO5br20b', [
    (S, 'GPIO5', B, 8.40, 19.42, 9.00, 18.80),
    (S, 'GPIO5', B, 9.00, 18.80, 9.60, 19.20),
    (V, 'GPIO5', 9.60, 19.20, 0.40, 0.20),
    (S, 'GPIO5', F, 9.60, 19.20, 9.60, 19.925),
])

try_chain('GNDr20b', [
    (S, 'GND', B, 5.70, 22.075, 5.15, 22.70),
    (V, 'GND', 5.15, 22.70, 0.40, 0.20),
])

pcbnew.SaveBoard(P, b)
print('saved')
