#!/usr/bin/env python3
"""Hand-finish round 1b for the redo_v2 routed board: v2 chains for the
6 pairs left after patch_finish_r1.py (STATUS_LED already applied)."""
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
    (S, 'GPIO9', F, 8.4, 19.93, 8.7, 20.5),
    (S, 'GPIO9', F, 8.7, 20.5, 8.7, 20.85),
    (S, 'GPIO9', F, 8.7, 20.85, 9.6, 20.85),
    (V, 'GPIO9', 9.6, 20.85),
    (S, 'GPIO9', B, 9.6, 20.85, 9.6, 19.93),
])
try_chain('GPIO11', [
    (S, 'GPIO11', F, 7.8, 19.93, 7.8, 20.75),
    (S, 'GPIO11', F, 7.8, 20.75, 7.15, 21.2),
    (S, 'GPIO11', F, 7.15, 21.2, 7.15, 21.9),
    (V, 'GPIO11', 7.15, 21.9),
    (S, 'GPIO11', B, 7.15, 21.9, 10.2, 21.9),
    (S, 'GPIO11', B, 10.2, 21.9, 10.2, 19.93),
])
try_chain('EX5', [
    (S, 'EX5', F, 10.7, 26.95, 10.45, 27.6),
    (V, 'EX5', 10.45, 27.6),
    (S, 'EX5', B, 10.45, 27.6, 11.55, 26.75),
    (S, 'EX5', B, 11.55, 26.75, 13.9, 26.77),
])
try_chain('EX2', [
    (S, 'EX2', F, 12.3, 24.2, 12.6, 24.45),
    (S, 'EX2', F, 12.6, 24.45, 16.3, 24.45),
    (V, 'EX2', 16.3, 24.45),
    (S, 'EX2', B, 16.3, 24.45, 16.3, 26.3),
    (S, 'EX2', B, 16.3, 26.3, 15.96, 26.3),
])
try_chain('3V3_SJ4', [
    (S, '3V3', B, 14.7, 28.7, 15.15, 29.1),
    (S, '3V3', B, 15.15, 29.1, 15.85, 29.8),
    (S, '3V3', B, 15.85, 29.8, 16.15, 30.05),
    (S, '3V3', B, 16.15, 30.05, 16.15, 31.3),
    (S, '3V3', B, 16.15, 31.3, 15.05, 31.3),
    (S, '3V3', B, 15.05, 31.3, 15.05, 31.05),
])
try_chain('FFC2_3', [
    (S, 'FFC2_3', B, 12.9, 27.6, 12.05, 28.5),
    (S, 'FFC2_3', B, 12.05, 28.5, 12.05, 29.6),
    (S, 'FFC2_3', B, 12.05, 29.6, 11.75, 30.35),
    (S, 'FFC2_3', B, 11.75, 30.35, 11.75, 30.6),
])

pcbnew.SaveBoard(P, b)
print('saved', P)
