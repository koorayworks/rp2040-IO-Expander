#!/usr/bin/env python3
"""Hand-finish round 5b: second attempts after r5a blocker map.
- EX2 tap via (12.75,24.60) (east of GPIO28's B vertical)
- EX5 tap via In1 west run at y26.30 (south of EX2's In1 vertical end)
- GPIO10 via F east run at y22.60 to (10.05,23.00)
- GPIO1 north detour at y18.55 around GPIO2's F vertical
- USB_D- gap A via (11.55,23.70) (west of JP3 pad1 rect)
- USB_D- gap B south loop on B at y25.70 + In1 diag to gap-A via
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

try_chain('EX2tap2', [
    (V, 'EX2', 12.75, 24.60),
    (S, 'EX2', I1, 12.75, 24.60, 12.40, 25.13),
    (S, 'EX2', F, 12.75, 24.60, 12.55, 24.20),
])

try_chain('EX5tap2', [
    (S, 'EX5', I1, 13.90, 25.78, 13.20, 26.30),
    (S, 'EX5', I1, 13.20, 26.30, 11.40, 26.30),
    (V, 'EX5', 11.40, 26.30),
    (S, 'EX5', F, 11.40, 26.30, 11.15, 26.60),
])

try_chain('GPIO10v2', [
    (S, 'GPIO10', F, 8.10, 22.60, 10.05, 22.60),
    (S, 'GPIO10', F, 10.05, 22.60, 10.05, 23.00),
    (V, 'GPIO10', 10.05, 23.00),
    (S, 'GPIO10', B, 10.05, 23.00, 9.90, 22.50),
    (S, 'GPIO10', B, 9.90, 22.50, 9.90, 22.20),
])

try_chain('GPIO1v2', [
    (S, 'GPIO1', F, 10.80, 19.25, 10.80, 18.55),
    (S, 'GPIO1', F, 10.80, 18.55, 7.75, 18.55),
    (V, 'GPIO1', 7.75, 18.55),
    (S, 'GPIO1', B, 7.75, 18.55, 7.20, 19.25),
])

try_chain('USB_A2', [
    (V, 'USB_D-', 11.55, 23.70),
])

try_chain('USB_B2', [
    (S, 'USB_D-', B, 6.30, 22.30, 6.30, 25.70),
    (S, 'USB_D-', B, 6.30, 25.70, 11.00, 25.70),
    (V, 'USB_D-', 11.00, 25.70),
    (S, 'USB_D-', I1, 11.00, 25.70, 11.55, 23.70),
])

pcbnew.SaveBoard(P, b)
print('saved')
