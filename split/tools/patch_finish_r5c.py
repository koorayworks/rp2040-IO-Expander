#!/usr/bin/env python3
"""Hand-finish round 5c: third attempts after r5b blocker map.
- EX2 tap: via (11.25,23.20) west pocket, F diag into JP3 pad1 NW,
  In1 south-west loop to the (12.40,25.13) endpoint
- EX5 tap: In1 south loop at y27.60 under VSYS/EX2 vertical ends
- GPIO10: F stub south to 22.90, east run, via (10.20,22.95)
- GPIO1: NW diag dodging GPIO7's via, west run at y18.55
- USB_D- A: via (11.62,23.78)
- USB_D- B: B thread x6.60 north, via (7.30,21.30), In2 east run
  into island B's In2 endpoint (11.35,21.30)
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

try_chain('EX2tap3', [
    (V, 'EX2', 11.25, 23.20),
    (S, 'EX2', F, 11.25, 23.20, 12.05, 23.50),
    (S, 'EX2', I1, 11.25, 23.20, 11.20, 24.60),
    (S, 'EX2', I1, 11.20, 24.60, 12.40, 25.13),
])

try_chain('EX5tap3', [
    (S, 'EX5', I1, 13.90, 25.78, 14.35, 27.60),
    (S, 'EX5', I1, 14.35, 27.60, 11.40, 27.60),
    (V, 'EX5', 11.40, 27.60),
    (S, 'EX5', F, 11.40, 27.60, 11.20, 26.90),
])

try_chain('GPIO10v3', [
    (S, 'GPIO10', F, 8.10, 22.70, 8.10, 22.90),
    (S, 'GPIO10', F, 8.10, 22.90, 10.05, 22.90),
    (S, 'GPIO10', F, 10.05, 22.90, 10.20, 22.95),
    (V, 'GPIO10', 10.20, 22.95),
    (S, 'GPIO10', B, 10.20, 22.95, 9.90, 22.50),
    (S, 'GPIO10', B, 9.90, 22.50, 9.90, 22.20),
])

try_chain('GPIO1v3', [
    (S, 'GPIO1', F, 10.80, 19.25, 10.05, 18.55),
    (S, 'GPIO1', F, 10.05, 18.55, 7.75, 18.55),
    (V, 'GPIO1', 7.75, 18.55),
    (S, 'GPIO1', B, 7.75, 18.55, 7.20, 19.25),
])

try_chain('USB_A3', [
    (V, 'USB_D-', 11.62, 23.78),
])

try_chain('USB_B3', [
    (S, 'USB_D-', B, 6.40, 22.07, 6.60, 22.07),
    (S, 'USB_D-', B, 6.60, 22.07, 6.60, 21.30),
    (S, 'USB_D-', B, 6.60, 21.30, 7.30, 21.30),
    (V, 'USB_D-', 7.30, 21.30),
    (S, 'USB_D-', I2, 7.30, 21.30, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
