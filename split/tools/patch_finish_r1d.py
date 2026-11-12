#!/usr/bin/env python3
"""Hand-finish round 1d: v3/v4/v5 chains for the remaining pairs."""
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
    (S, 'GPIO9', F, 8.4, 19.93, 6.5, 20.7),
    (S, 'GPIO9', F, 6.5, 20.7, 6.5, 21.5),
    (V, 'GPIO9', 6.5, 21.5),
    (S, 'GPIO9', B, 6.5, 21.5, 9.6, 21.5),
    (S, 'GPIO9', B, 9.6, 21.5, 9.6, 19.93),
])
try_chain('GPIO11', [
    (S, 'GPIO11', F, 7.8, 19.93, 8.45, 19.0),
    (S, 'GPIO11', F, 8.45, 19.0, 9.5, 18.2),
    (S, 'GPIO11', F, 9.5, 18.2, 10.9, 16.59),
    (V, 'GPIO11', 10.9, 16.59),
])
try_chain('EX5', [
    (S, 'EX5', F, 10.7, 26.95, 10.6, 27.6),
    (V, 'EX5', 10.6, 27.6),
    (S, 'EX5', B, 10.6, 27.6, 11.5, 26.5),
    (S, 'EX5', B, 11.5, 26.5, 13.9, 26.5),
    (S, 'EX5', B, 13.9, 26.5, 13.9, 26.77),
])
try_chain('EX2', [
    (S, 'EX2', F, 12.3, 24.15, 14.6, 24.15),
    (S, 'EX2', F, 14.6, 24.15, 14.8, 24.5),
    (V, 'EX2', 14.8, 24.5),
    (S, 'EX2', B, 14.8, 24.5, 14.8, 26.3),
    (S, 'EX2', B, 14.8, 26.3, 15.96, 26.3),
])
try_chain('3V3_SJ4', [
    (S, '3V3', F, 14.7, 28.7, 14.75, 27.05),
    (S, '3V3', F, 14.75, 27.05, 17.2, 27.05),
    (S, '3V3', F, 17.2, 27.05, 17.2, 27.2),
    (V, '3V3', 17.2, 27.2),
    (S, '3V3', B, 17.2, 27.2, 17.2, 32.15),
    (S, '3V3', B, 17.2, 32.15, 15.05, 32.15),
    (S, '3V3', B, 15.05, 32.15, 15.05, 31.05),
])
try_chain('FFC2_3', [
    (S, 'FFC2_3', B, 12.9, 27.6, 12.35, 28.9),
    (S, 'FFC2_3', B, 12.35, 28.9, 12.05, 29.6),
    (S, 'FFC2_3', B, 12.05, 29.6, 11.75, 30.35),
    (S, 'FFC2_3', B, 11.75, 30.35, 11.75, 30.6),
])

pcbnew.SaveBoard(P, b)
print('saved', P)
