#!/usr/bin/env python3
"""Hand-finish round 22a (redo_v22 board, last 2 pairs):
- GND: J2.2's B stub (13.2,19.925)->(13.2,19.25) dead-ends;
  B jog + via (12.6,19.0) + F onto the web track end
  (12.3,19.463)
- GPIO27: J1.6 bare; F dive north + via (6.0,19.0) + I1 ride
  east onto the web's I1 track end (13.616,14.864)
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

try_chain('GNDr22a', [
    (S, 'GND', B, 13.20, 19.25, 13.65, 19.60),
    (V, 'GND', 13.65, 19.60, 0.40, 0.20),
    (S, 'GND', F, 13.65, 19.60, 12.30, 19.463),
])

try_chain('GPIO27r22a', [
    (S, 'GPIO27', F, 6.05, 19.925, 6.10, 21.20),
    (V, 'GPIO27', 6.10, 21.20, 0.40, 0.20),
    (S, 'GPIO27', I1, 6.10, 21.20, 13.616, 14.864),
])

pcbnew.SaveBoard(P, b)
print('saved')
