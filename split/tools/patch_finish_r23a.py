#!/usr/bin/env python3
"""Hand-finish round 23a (redo_v23 board, last pair):
GPIO7: U1.26's F ride dead-ends at via (10.04,13.823);
J1.16/J2.16 hold only the dive via. Close on F from the
U1 pad: (9.8,17.363)->(10.75,19.0) slips E of GPIO1's F
diagonal east end (9.89,18.23) by 0.255, then W along the
near-row band onto J1.16 (9.0,19.925), clearing J1.17's
rect corner by 0.223.
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

try_chain('GPIO7r23a', [
    (S, 'GPIO7', I2, 10.04, 13.823, 9.75, 14.35),
    (S, 'GPIO7', I2, 9.75, 14.35, 11.45, 14.35),
    (S, 'GPIO7', I2, 11.45, 14.35, 9.85, 14.40),
    (S, 'GPIO7', I2, 9.85, 14.40, 10.85, 14.40),
    (S, 'GPIO7', I2, 10.85, 14.40, 11.60, 15.30),
    (S, 'GPIO7', I2, 11.60, 15.30, 12.50, 16.50),
    (S, 'GPIO7', I2, 12.50, 16.50, 5.28, 16.45),
    (S, 'GPIO7', I2, 5.28, 16.45, 5.28, 18.30),
    (S, 'GPIO7', I2, 5.28, 18.30, 7.20, 18.60),
    (S, 'GPIO7', I2, 7.20, 18.60, 8.10, 18.35),
    (S, 'GPIO7', I2, 8.10, 18.35, 9.00, 19.925),
])

pcbnew.SaveBoard(P, b)
print('saved')
