#!/usr/bin/env python3
"""Hand-finish r30d: USB_D+ only (designed from the real
r30 pocket dump). I2 staircase NE between the fence ends
(GPIO11 y=20.12 x<=7.45 / GPIO10 y=19.84 x<=7.74 /
GPIO9 y=19.57 x<=7.89), east along y~19.45, via at
(10.8,19.42), F hop along y~19.40 to J1.26's stub end.
GPIO1/GPIO9 have no hand chain on r30 (verified against
the full pocket geometry).
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

try_chain('USBDPr30d', [
    (S, 'USB_D+', I2, 6.00, 20.60, 6.95, 20.77),
    (S, 'USB_D+', I2, 6.95, 20.77, 7.10, 20.85),
    (S, 'USB_D+', I2, 7.10, 20.85, 7.65, 21.60),
    (S, 'USB_D+', I2, 7.65, 21.60, 8.70, 23.40),
    (S, 'USB_D+', I2, 8.70, 23.40, 11.30, 22.60),
    (S, 'USB_D+', I2, 11.30, 22.60, 11.30, 21.60),
    (V, 'USB_D+', 11.30, 21.60, 0.40, 0.20),
    (S, 'USB_D+', F, 11.30, 21.60, 11.35, 20.45),
    (S, 'USB_D+', F, 11.35, 20.45, 12.00, 19.398),
])

pcbnew.SaveBoard(P, b)
print('saved')
