#!/usr/bin/env python3
"""Hand-finish for the round-1 (redo_v2) routed module board: close the
7 remaining unconnected pairs. Each net has a candidate chain; every
element is checker-verified, and a chain that fails partway is rolled
back so a revised chain can be tried on the next run."""
import os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker import check_seg, check_via

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
P = os.path.join(ROOT, 'split', 'module_board', 'module_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
mm = pcbnew.FromMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu

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
try_chain('STATUS_LED', [
    (S, 'STATUS_LED', B, 4.65, 16.32, 4.65, 19.30),
    (S, 'STATUS_LED', B, 4.65, 19.30, 4.80, 19.575),
])
try_chain('GPIO9', [
    (S, 'GPIO9', F, 8.4, 19.93, 8.4, 20.85),
    (S, 'GPIO9', F, 8.4, 20.85, 9.6, 20.85),
    (V, 'GPIO9', 9.6, 20.85),
    (S, 'GPIO9', B, 9.6, 20.85, 9.6, 19.93),
])
try_chain('GPIO11', [
    (S, 'GPIO11', F, 7.8, 19.93, 7.8, 21.0),
    (S, 'GPIO11', F, 7.8, 21.0, 8.15, 21.0),
    (S, 'GPIO11', F, 8.15, 21.0, 8.75, 21.35),
    (S, 'GPIO11', F, 8.75, 21.35, 10.2, 21.35),
    (V, 'GPIO11', 10.2, 21.35),
    (S, 'GPIO11', B, 10.2, 21.35, 10.2, 19.93),
])
try_chain('EX5', [
    (S, 'EX5', F, 11.05, 26.5, 11.95, 26.77),
    (V, 'EX5', 11.95, 26.77),
    (S, 'EX5', B, 11.95, 26.77, 13.9, 26.77),
])
try_chain('EX2', [
    (S, 'EX2', F, 12.05, 24.1, 11.9, 25.6),
    (V, 'EX2', 11.9, 25.6),
    (S, 'EX2', B, 11.9, 25.6, 12.97, 26.52),
])
try_chain('3V3_SJ4', [
    (S, '3V3', B, 14.7, 28.7, 15.15, 29.1),
    (S, '3V3', B, 15.15, 29.1, 15.3, 29.5),
    (S, '3V3', B, 15.3, 29.5, 15.05, 30.18),
])
try_chain('FFC2_3', [
    (S, 'FFC2_3', B, 12.9, 27.6, 12.25, 28.2),
    (S, 'FFC2_3', B, 12.25, 28.2, 12.25, 29.6),
    (S, 'FFC2_3', B, 12.25, 29.6, 11.75, 30.35),
    (S, 'FFC2_3', B, 11.75, 30.35, 11.75, 30.6),
])

pcbnew.SaveBoard(P, b)
print('saved', P)
