#!/usr/bin/env python3
"""Hand-finish round 8d (redo_v8 board, after r8a/b applied GPIO7+EX5):
- GPIO3a v4: via (7.58,18.5) west of GPIO5's I2 vertical, B tap from
  the chain, F jog east into U1.22
- GPIO3b v4: via (10.95,22.35) south of USB_D+'s I1 rail
- GPIO4 v4: via (9.3,24.55), south of USB_D-'s I1 rail
- GPIO26 v4: via (5.75,22.95) SW, clear of USB_D-'s via (6.3,22.85)
- GPIO2 v4: I1 dive to (11.85,18.7), jog to (10.45,20.15), via
  (11.0,21.5), F along the far row into J1.21
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

try_chain('GPIO3ar8d', [
    (S, 'GPIO3', B, 7.966, 18.50, 7.58, 18.50),
    (V, 'GPIO3', 7.58, 18.50),
    (S, 'GPIO3', F, 7.58, 18.50, 8.05, 18.10),
    (S, 'GPIO3', F, 8.05, 18.10, 8.28, 17.3635),
])

try_chain('GPIO3br8d', [
    (V, 'GPIO3', 10.95, 22.35),
    (S, 'GPIO3', F, 10.20, 19.925, 10.95, 22.35),
    (S, 'GPIO3', B, 10.95, 22.35, 10.60, 20.35),
    (S, 'GPIO3', B, 10.60, 20.35, 8.30, 19.05),
    (S, 'GPIO3', B, 8.30, 19.05, 7.966, 19.232),
])

try_chain('GPIO4r8d', [
    (V, 'GPIO4', 9.30, 24.55),
    (S, 'GPIO4', F, 9.90, 22.075, 9.30, 24.55),
    (S, 'GPIO4', B, 9.30, 24.55, 7.00, 23.30),
])

try_chain('GPIO26r8d', [
    (V, 'GPIO26', 5.75, 22.95),
    (S, 'GPIO26', F, 6.30, 22.075, 5.75, 22.95),
    (S, 'GPIO26', I2, 5.75, 22.95, 10.00, 21.15),
    (S, 'GPIO26', I2, 10.00, 21.15, 11.435, 20.97),
])

try_chain('GPIO2r8d', [
    (S, 'GPIO2', I1, 8.669, 14.379, 11.85, 18.70),
    (S, 'GPIO2', I1, 11.85, 18.70, 10.45, 20.15),
    (S, 'GPIO2', I1, 10.45, 20.15, 11.00, 21.50),
    (V, 'GPIO2', 11.00, 21.50),
    (S, 'GPIO2', F, 11.00, 21.50, 11.00, 22.075),
    (S, 'GPIO2', F, 11.00, 22.075, 10.50, 22.075),
    (S, 'GPIO2', B, 11.00, 21.50, 7.50, 21.30),
    (V, 'GPIO2', 7.50, 21.30),
    (S, 'GPIO2', B, 7.50, 21.30, 7.50, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
