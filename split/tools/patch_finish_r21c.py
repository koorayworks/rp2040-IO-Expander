#!/usr/bin/env python3
"""Hand-finish round 21c (redo_v21 board):
- GPIO2: I1 further west around GPIO8's seeded I1 lead:
  (10.6,14.6)->(9.45,18.4)->(10.5,21.3)
- GPIO5 main: via moved W to (10.05,17.2) (U1.28's rect
  fenced (10.45,17.2)); I1 exits east then south:
  (10.05,17.2)->(10.7,17.5)->(10.45,18.9)->(9.6,19.0)
- GPIO5 J2: jog point NE to (8.8,18.9) -- (8.75,19.05) sat
  0.13 from GPIO9's B segment middle
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

try_chain('GPIO2r21c', [
    (S, 'GPIO2', I1, 10.60, 14.60, 9.45, 18.40),
    (S, 'GPIO2', I1, 9.45, 18.40, 10.50, 21.30),
])

try_chain('GPIO5r21c-main', [
    (S, 'GPIO5', I2, 8.87, 15.36, 10.05, 17.20),
    (V, 'GPIO5', 10.05, 17.20, 0.40, 0.20),
    (S, 'GPIO5', I1, 10.05, 17.20, 10.70, 17.50),
    (S, 'GPIO5', I1, 10.70, 17.50, 10.45, 18.90),
    (S, 'GPIO5', I1, 10.45, 18.90, 9.60, 19.00),
])

try_chain('GPIO5r21c-j2', [
    (S, 'GPIO5', B, 8.40, 19.42, 8.80, 18.90),
    (S, 'GPIO5', B, 8.80, 18.90, 8.95, 18.80),
    (V, 'GPIO5', 8.95, 18.80, 0.40, 0.20),
    (S, 'GPIO5', I1, 8.95, 18.80, 9.60, 19.00),
])

pcbnew.SaveBoard(P, b)
print('saved')
