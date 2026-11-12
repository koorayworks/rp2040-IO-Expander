#!/usr/bin/env python3
"""Hand-finish round 5h: eighth attempts after r5g blocker map.
- GPIO10: F thread north between J1 pad12/pad14 rects at x8.10,
  via (8.10,20.60), B diag to J2 pad13 rect
- GPIO1: F exit via the pad20/pad22 gap at x10.50, west at y20.35
- USB_D- B: west at y22.30 (GPIO28 via dodged), far-west loop
  x4.90, via (5.30,23.30) from the west, In2 east run
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

try_chain('GPIO10v8', [
    (S, 'GPIO10', F, 8.10, 21.90, 8.10, 20.60),
    (V, 'GPIO10', 8.10, 20.60),
    (S, 'GPIO10', B, 8.10, 20.60, 9.90, 21.50),
    (S, 'GPIO10', B, 9.90, 21.50, 9.90, 22.10),
])

try_chain('GPIO1v8', [
    (S, 'GPIO1', F, 10.50, 20.20, 10.50, 20.35),
    (S, 'GPIO1', F, 10.50, 20.35, 7.60, 20.35),
    (S, 'GPIO1', F, 7.60, 20.35, 7.20, 20.60),
    (V, 'GPIO1', 7.20, 20.60),
    (S, 'GPIO1', B, 7.20, 20.60, 7.20, 19.93),
])

try_chain('USB_B8', [
    (S, 'USB_D-', B, 6.30, 22.07, 6.30, 22.30),
    (S, 'USB_D-', B, 6.30, 22.30, 4.90, 22.30),
    (S, 'USB_D-', B, 4.90, 22.30, 4.90, 23.30),
    (S, 'USB_D-', B, 4.90, 23.30, 5.30, 23.30),
    (V, 'USB_D-', 5.30, 23.30),
    (S, 'USB_D-', I2, 5.30, 23.30, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
