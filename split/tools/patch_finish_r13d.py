#!/usr/bin/env python3
"""Hand-finish round 13d (redo_v13 board):
- USB_D+ v4: B ride east to via (6.7,20.95), over USB_D-'s rect
  corner (0.228) and clear of GPIO2's I2 track end + GPIO15's via
- GPIO3b v4: I2 ride jogged west around GPIO5's via (9.17,18.54):
  (8.2,15.6)->(8.45,18.2)->(10.15,20.7)
(GPIO3a and GPIO1, GPIO4: fenced in r13 copper -- round-14 seeds)
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

try_chain('USBDPr13d', [
    (S, 'USB_D+', B, 6.00, 19.925, 6.70, 20.95),
    (V, 'USB_D+', 6.70, 20.95),
    (S, 'USB_D+', I2, 6.70, 20.95, 11.95, 20.90),
    (V, 'USB_D+', 11.95, 20.90),
    (S, 'USB_D+', F, 11.95, 20.90, 12.127, 19.271),
])

try_chain('GPIO3br13d', [
    (S, 'GPIO3', I2, 8.20, 15.60, 8.45, 18.20),
    (S, 'GPIO3', I2, 8.45, 18.20, 10.15, 20.70),
])

pcbnew.SaveBoard(P, b)
print('saved')
