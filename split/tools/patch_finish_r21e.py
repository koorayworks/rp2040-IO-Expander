#!/usr/bin/env python3
"""Hand-finish round 21e (redo_v21 board):
- GPIO2: I1 around GPIO8's lead south end (11.12,18.95) and
  east of GPIO6's rail end (11.30,19.4):
  (10.6,14.6)->(11.5,19.3)->(11.58,20.4)->(10.5,21.3)
- GPIO5 main: I1 west around GPIO3's diagonal start
  (8.46,16.39): (8.87,15.36)->(8.15,16.1)->(8.15,17.5)
  ->(9.6,19.0)
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

try_chain('GPIO2r21e', [
    (S, 'GPIO2', I1, 10.60, 14.60, 11.50, 19.30),
    (S, 'GPIO2', I1, 11.50, 19.30, 11.58, 20.40),
    (S, 'GPIO2', I1, 11.58, 20.40, 10.50, 21.30),
])

try_chain('GPIO5r21e-main', [
    (S, 'GPIO5', I1, 8.87, 15.36, 8.15, 16.10),
    (S, 'GPIO5', I1, 8.15, 16.10, 8.15, 17.50),
    (S, 'GPIO5', I1, 8.15, 17.50, 9.60, 19.00),
])

pcbnew.SaveBoard(P, b)
print('saved')
