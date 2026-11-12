#!/usr/bin/env python3
"""Hand-finish round 1h: remaining 5 pairs, fence-aware chains."""
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
try_chain('GPIO11', [
    (S, 'GPIO11', F, 7.8, 19.93, 8.22, 18.9),
    (S, 'GPIO11', F, 8.22, 18.9, 8.5, 18.42),
    (S, 'GPIO11', F, 8.5, 18.42, 9.3, 18.45),
    (S, 'GPIO11', F, 9.3, 18.45, 10.9, 16.59),
    (V, 'GPIO11', 10.9, 16.59),
])
try_chain('GPIO9', [
    (S, 'GPIO9', F, 8.4, 19.93, 8.44, 19.05),
    (S, 'GPIO9', F, 8.44, 19.05, 8.45, 18.45),
    (S, 'GPIO9', F, 8.45, 18.45, 9.35, 18.47),
    (S, 'GPIO9', F, 9.35, 18.47, 10.33, 16.5),
    (V, 'GPIO9', 10.33, 16.5),
])
try_chain('EX2', [
    (S, 'EX2', F, 12.05, 24.1, 12.9, 24.52),
    (S, 'EX2', F, 12.9, 24.52, 13.28, 24.44),
    (S, 'EX2', F, 13.28, 24.44, 13.35, 24.38),
    (S, 'EX2', F, 13.35, 24.38, 13.6, 24.05),
    (S, 'EX2', F, 13.6, 24.05, 14.6, 24.05),
    (S, 'EX2', F, 14.6, 24.05, 14.8, 24.5),
    (V, 'EX2', 14.8, 24.5),
    (S, 'EX2', B, 14.8, 24.5, 14.8, 26.3),
    (S, 'EX2', B, 14.8, 26.3, 15.96, 26.3),
])
try_chain('3V3_SJ4', [
    (S, '3V3', B, 14.7, 28.7, 13.8, 28.9),
    (S, '3V3', B, 13.8, 28.9, 14.3, 29.3),
    (S, '3V3', B, 14.3, 29.3, 15.3, 30.35),
    (S, '3V3', B, 15.3, 30.35, 15.05, 30.42),
])
try_chain('FFC2_3', [
    (S, 'FFC2_3', B, 12.9, 27.6, 12.72, 28.45),
    (S, 'FFC2_3', B, 12.72, 28.45, 12.3, 29.1),
    (S, 'FFC2_3', B, 12.3, 29.1, 12.6, 29.95),
    (S, 'FFC2_3', B, 12.6, 29.95, 13.0, 30.6),
])

pcbnew.SaveBoard(P, b)
print('saved', P)
