#!/usr/bin/env python3
"""Graft r30e: copy the PROVEN r33 USB_D+ south I2 anchor
(closed USB_D+ in rounds 33/34/35) onto the r30 board,
plus an F hop up the x=12.0 slot between the J1.25/J1.27
pads to J1.26's stub end (12.0,19.398). Checker decides
every element against the real r30 copper; any FAIL
rolls the whole chain back.
"""
import os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker import check_seg, check_via

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
P = os.path.join(ROOT, 'split', 'module_board', 'backup',
                 'handfinish_work.kicad_pcb')
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

try_chain('USBDPr30e', [
    (S, 'USB_D+', I2, 6.00, 20.60, 5.20, 21.60),
    (S, 'USB_D+', I2, 5.20, 21.60, 4.60, 22.50),
    # first leg jogged W: on r30, GPIO0's I2 stub runs
    # (6.3,21.1)->(5.86,21.1) across the placement path
    (S, 'USB_D+', I2, 4.60, 22.50, 5.00, 23.90),
    (S, 'USB_D+', I2, 5.00, 23.90, 8.20, 23.95),
    (S, 'USB_D+', I2, 8.20, 23.95, 10.60, 23.50),
    (S, 'USB_D+', I2, 10.60, 23.50, 11.20, 22.95),
    (V, 'USB_D+', 11.20, 22.95, 0.40, 0.20),
    (S, 'USB_D+', F, 11.20, 22.95, 12.00, 22.60),
    (S, 'USB_D+', F, 12.00, 22.60, 12.00, 19.398),
])

pcbnew.SaveBoard(P, b)
print('saved')
