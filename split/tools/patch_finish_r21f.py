#!/usr/bin/env python3
"""Hand-finish round 21f (redo_v21 board):
- GPIO2: I1 is fenced (GPIO8 via/lead W, 3V3 via (11.4,18.3)
  E, GPIO6 rail S). Go I2 west around STATUS_LED's rail end
  (5.54,17.61), hopping to I1 to cross under the rail:
  I2 (8.669,14.379)->(5.6,17.2), via, I1 (5.6,17.2)->
  (5.6,18.05), via, I2 (5.6,18.05)->(8.574,19.372)
- GPIO5 main: I1 through the 1.4-degree window between
  GPIO3's tip via (8.2,15.6) and its diagonal start
  (8.46,16.39): (8.87,15.36)->(7.71,16.99)->(9.6,19.0)
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

try_chain('GPIO2r21f', [
    (S, 'GPIO2', I2, 8.669, 14.379, 5.60, 17.20),
    (V, 'GPIO2', 5.60, 17.20, 0.40, 0.20),
    (S, 'GPIO2', I1, 5.60, 17.20, 5.60, 18.05),
    (V, 'GPIO2', 5.60, 18.05, 0.40, 0.20),
    (S, 'GPIO2', I2, 5.60, 18.05, 8.574, 19.372),
])

try_chain('GPIO5r21f-main', [
    (S, 'GPIO5', I1, 8.87, 15.36, 7.71, 16.99),
    (S, 'GPIO5', I1, 7.71, 16.99, 9.60, 19.00),
])

pcbnew.SaveBoard(P, b)
print('saved')
