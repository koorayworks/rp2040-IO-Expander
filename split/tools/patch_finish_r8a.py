#!/usr/bin/env python3
"""Hand-finish round 8a (redo_v8 board): close the 10 remaining pairs.
- EX5: via on the I1 rail at (10.9,25.791) + F drop into JP4 pad1
- GPIO7: single via-in-pad at (9.0,19.925) joining J1.16 (F) to the
  B track that ends at the same XY (J2.16's stub)
- GPIO5: via beside the I2 chain end + B hop into J2.18
- GPIO1: via (7.35,18.5) joining J2.22's B stub to the F seed chain
- GPIO3a: U1.22 hop via (8.2,18.3) from the B chain
- GPIO3b: J1.20 hop via (10.2,20.6) from the B chain
- GPIO4: J1.19 hop via (9.3,23.1) to the B rail / via (7.0,23.3)
- GPIO26: J1.7 long I2 ride to via (11.435,20.97)'s chain
- GPIO2: I1 far-east loop (same plan as r7k, against r8 copper)
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

try_chain('EX5r8a', [
    (V, 'EX5', 10.90, 25.791),
    (S, 'EX5', F, 10.90, 25.791, 10.90, 26.60),
])

try_chain('GPIO7r8a', [
    (V, 'GPIO7', 9.00, 19.925),
])

try_chain('GPIO5r8a', [
    (V, 'GPIO5', 8.15, 19.35),
    (S, 'GPIO5', B, 8.15, 19.35, 8.40, 19.925),
])

try_chain('GPIO1r8a', [
    (V, 'GPIO1', 7.35, 18.50),
    (S, 'GPIO1', B, 7.20, 19.25, 7.35, 18.50),
    (S, 'GPIO1', F, 7.35, 18.50, 7.40, 18.10),
])

try_chain('GPIO3ar8a', [
    (S, 'GPIO3', B, 7.966, 18.30, 8.20, 18.30),
    (V, 'GPIO3', 8.20, 18.30),
    (S, 'GPIO3', F, 8.20, 18.30, 8.20, 17.3635),
])

try_chain('GPIO3br8a', [
    (V, 'GPIO3', 10.20, 20.60),
    (S, 'GPIO3', F, 10.20, 19.925, 10.20, 20.60),
    (S, 'GPIO3', B, 10.20, 20.60, 8.60, 19.60),
    (S, 'GPIO3', B, 8.60, 19.60, 7.966, 19.232),
])

try_chain('GPIO4r8a', [
    (V, 'GPIO4', 9.30, 23.10),
    (S, 'GPIO4', F, 9.90, 22.075, 9.30, 23.10),
    (S, 'GPIO4', B, 9.30, 23.10, 7.00, 23.30),
])

try_chain('GPIO26r8a', [
    (V, 'GPIO26', 6.30, 20.85),
    (S, 'GPIO26', F, 6.30, 22.075, 6.30, 20.85),
    (S, 'GPIO26', I2, 6.30, 20.85, 11.435, 20.97),
])

try_chain('GPIO2r8a', [
    (S, 'GPIO2', I1, 8.669, 14.379, 11.95, 15.00),
    (S, 'GPIO2', I1, 11.95, 15.00, 10.50, 21.30),
    (V, 'GPIO2', 10.50, 21.30),
    (S, 'GPIO2', F, 10.50, 21.30, 10.50, 22.075),
    (S, 'GPIO2', B, 10.50, 21.30, 7.50, 21.30),
    (V, 'GPIO2', 7.50, 21.30),
    (S, 'GPIO2', B, 7.50, 21.30, 7.50, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
