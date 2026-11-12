#!/usr/bin/env python3
"""Hand-finish round 20a (redo_v20 board, 6 pairs):
- GPIO4: U1 seed via (8.58,15.98) dead-ends; I1 (or I2) vertical
  south onto the web's y=23.306 horizontal
- EX5: J4 island via (13.88,25.74) dead-ends; I2 west onto the
  web endpoint (10.9,25.629)
- USB_D-: J1.25 bare; F dive + via (11.7,23.3) + I1 onto the
  web's (11.7,24.379) cluster
- GPIO5a: J1.18 bare; F chain onto U1's ride end (9.0,16.55)
- GPIO5b: J2 stub end (8.4,19.42); B ride + via (9.6,19.2) +
  F up into J1.18
- GND: J2 tab pad (5.7,22.075); B lead + via (5.5,22.9) hoping
  the In1 zone copper is there (DRC decides)
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

ok = try_chain('GPIO4r20a-I1', [
    (S, 'GPIO4', I1, 8.58, 15.98, 8.58, 23.306),
])
if not ok:
    try_chain('GPIO4r20a-I2', [
        (S, 'GPIO4', I2, 8.58, 15.98, 8.58, 23.306),
        (V, 'GPIO4', 8.58, 23.306, 0.40, 0.20),
        (S, 'GPIO4', I1, 8.58, 23.306, 8.58, 23.306),
    ])

try_chain('EX5r20a', [
    (S, 'EX5', I2, 13.88, 25.74, 10.90, 25.629),
])

try_chain('USBD-r20a', [
    (S, 'USB_D-', F, 11.70, 22.075, 11.70, 23.30),
    (V, 'USB_D-', 11.70, 23.30, 0.40, 0.20),
    (S, 'USB_D-', I1, 11.70, 23.30, 11.70, 24.379),
])

try_chain('GPIO5ar20a', [
    (S, 'GPIO5', F, 9.60, 19.925, 9.30, 18.30),
    (S, 'GPIO5', F, 9.30, 18.30, 9.00, 16.55),
])

try_chain('GPIO5br20a', [
    (S, 'GPIO5', B, 8.40, 19.42, 9.60, 19.20),
    (V, 'GPIO5', 9.60, 19.20, 0.40, 0.20),
    (S, 'GPIO5', F, 9.60, 19.20, 9.60, 19.925),
])

try_chain('GNDr20a', [
    (S, 'GND', B, 5.70, 22.075, 5.50, 22.90),
    (V, 'GND', 5.50, 22.90, 0.40, 0.20),
])

pcbnew.SaveBoard(P, b)
print('saved')
