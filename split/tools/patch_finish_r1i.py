#!/usr/bin/env python3
"""Hand-finish round 1i: dive/west routes for GPIO11+GPIO9, via-hop EX2,
refined 3V3 + FFC2_3."""
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
    (S, 'GPIO11', F, 7.8, 19.93, 6.8, 20.9),
    (V, 'GPIO11', 6.8, 20.9),
    (S, 'GPIO11', B, 6.8, 20.9, 7.6, 21.45),
    (S, 'GPIO11', B, 7.6, 21.45, 10.85, 21.45),
    (S, 'GPIO11', B, 10.85, 21.45, 10.85, 19.7),
    (S, 'GPIO11', B, 10.85, 19.7, 10.18, 19.2),
])
try_chain('GPIO9', [
    (S, 'GPIO9', F, 8.4, 19.25, 8.4, 19.08),
    (S, 'GPIO9', F, 8.4, 19.08, 6.75, 19.66),
    (V, 'GPIO9', 6.75, 19.66),
    (S, 'GPIO9', B, 6.75, 19.66, 6.15, 21.25),
    (S, 'GPIO9', B, 6.15, 21.25, 7.4, 21.55),
    (S, 'GPIO9', B, 7.4, 21.55, 7.7, 21.7),
    (S, 'GPIO9', B, 7.7, 21.7, 9.9, 21.7),
    (S, 'GPIO9', B, 9.9, 21.7, 9.75, 20.2),
    (S, 'GPIO9', B, 9.75, 20.2, 9.6, 19.7),
])
try_chain('EX2', [
    (S, 'EX2', F, 12.3, 24.2, 12.15, 24.6),
    (V, 'EX2', 12.15, 24.6),
    (S, 'EX2', B, 12.15, 24.6, 14.3, 25.15),
    (S, 'EX2', B, 14.3, 25.15, 15.2, 26.3),
])
try_chain('3V3_SJ4', [
    (S, '3V3', B, 14.7, 28.7, 13.35, 28.47),
    (S, '3V3', B, 13.35, 28.47, 14.3, 28.45),
    (S, '3V3', B, 14.3, 28.45, 15.35, 29.6),
    (S, '3V3', B, 15.35, 29.6, 15.05, 30.42),
])
try_chain('FFC2_3', [
    (S, 'FFC2_3', B, 12.9, 27.6, 12.72, 28.45),
    (S, 'FFC2_3', B, 12.72, 28.45, 12.3, 29.1),
    (S, 'FFC2_3', B, 12.3, 29.1, 12.75, 29.9),
    (S, 'FFC2_3', B, 12.75, 29.9, 13.0, 30.6),
])

pcbnew.SaveBoard(P, b)
print('saved', P)
