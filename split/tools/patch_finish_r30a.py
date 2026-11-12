#!/usr/bin/env python3
"""Hand-finish round 30a (redo_v30 board, 3 pairs left).
GPIO1: via at (7.35,19.15) off the J2 stub tip + F climb
to the wall stub end (7.4,18.1).
GPIO9: B ride from J2.14's stub tip to its own via
(8.4,18.98).
USB_D+: inner ride from the B island's via (6.0,20.6)
east to a new via under J1.26's F stub.
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

try_chain('GPIO1r30a', [
    (S, 'GPIO1', B, 7.20, 19.25, 7.35, 19.15),
    (V, 'GPIO1', 7.35, 19.15, 0.40, 0.20),
    (S, 'GPIO1', F, 7.35, 19.15, 7.40, 18.10),
])

try_chain('GPIO9r30a', [
    (S, 'GPIO9', B, 9.60, 19.25, 8.40, 18.98),
])

try_chain('USBDPr30a', [
    (S, 'USB_D+', I1, 6.00, 20.60, 11.90, 20.30),
    (V, 'USB_D+', 11.90, 20.30, 0.40, 0.20),
    (S, 'USB_D+', F, 11.90, 20.30, 12.00, 19.398),
])

pcbnew.SaveBoard(P, b)
print('saved')
