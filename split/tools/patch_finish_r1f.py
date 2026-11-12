#!/usr/bin/env python3
"""Hand-finish round 1f: remaining 5 pairs (GPIO9/GPIO11/EX2/3V3/FFC2_3)."""
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
try_chain('GPIO9', [
    (V, 'GPIO9', 8.32, 19.7),
    (S, 'GPIO9', B, 8.32, 19.7, 9.35, 20.45),
    (S, 'GPIO9', B, 9.35, 20.45, 9.6, 19.6),
])
try_chain('GPIO11', [
    (S, 'GPIO11', F, 7.8, 19.93, 8.3, 19.0),
    (S, 'GPIO11', F, 8.3, 19.0, 8.6, 18.98),
    (S, 'GPIO11', F, 8.6, 18.98, 8.72, 18.5),
    (S, 'GPIO11', F, 8.72, 18.5, 9.3, 18.45),
    (S, 'GPIO11', F, 9.3, 18.45, 10.9, 16.59),
    (V, 'GPIO11', 10.9, 16.59),
])
try_chain('EX2', [
    (S, 'EX2', F, 12.05, 24.1, 12.9, 24.52),
    (S, 'EX2', F, 12.9, 24.52, 13.28, 24.44),
    (S, 'EX2', F, 13.28, 24.44, 13.5, 24.2),
    (S, 'EX2', F, 13.5, 24.2, 13.85, 24.12),
    (S, 'EX2', F, 13.85, 24.12, 14.6, 24.12),
    (S, 'EX2', F, 14.6, 24.12, 14.8, 24.5),
    (V, 'EX2', 14.8, 24.5),
    (S, 'EX2', B, 14.8, 24.5, 14.8, 26.3),
    (S, 'EX2', B, 14.8, 26.3, 15.96, 26.3),
])
try_chain('3V3_SJ4', [
    (S, '3V3', B, 14.7, 28.7, 14.0, 29.45),
    (S, '3V3', B, 14.0, 29.45, 14.55, 29.8),
    (S, '3V3', B, 14.55, 29.8, 14.55, 30.15),
])
try_chain('FFC2_3', [
    (S, 'FFC2_3', B, 12.9, 27.6, 12.72, 28.45),
    (S, 'FFC2_3', B, 12.72, 28.45, 12.3, 29.1),
    (S, 'FFC2_3', B, 12.3, 29.1, 12.05, 29.6),
    (S, 'FFC2_3', B, 12.05, 29.6, 11.75, 30.35),
    (S, 'FFC2_3', B, 11.75, 30.35, 11.75, 30.6),
])

pcbnew.SaveBoard(P, b)
print('saved', P)
