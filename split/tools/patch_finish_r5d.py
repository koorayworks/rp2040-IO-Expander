#!/usr/bin/env python3
"""Hand-finish round 5d: fourth attempts after r5c blocker map.
- EX2 tap: via (10.65,22.75), F east at y22.80 then into JP3 pad1,
  In1 loop (11.20,24.60) -> (12.40,25.13)
- EX5 tap: In1 south loop at y28.85 (VSYS vertical ends 28.45)
- GPIO10: F diag to (8.55,22.90), via, In1 diag to (9.90,22.80), via
  on J2 pad13's column south of both pad rects, B into pad13 rect
- GPIO1: F south exit from J1 pad22, west at y21.00, via (7.20,21.00),
  B north into J2 pad22's stub
- USB_D- B: thread x6.42, east at y21.55 (GPIO12 via dodged),
  via (7.30,21.55), In2 run to island B endpoint (11.35,21.30)
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

try_chain('EX2tap4', [
    (V, 'EX2', 10.65, 22.75),
    (S, 'EX2', F, 10.65, 22.75, 11.90, 22.80),
    (S, 'EX2', F, 11.90, 22.80, 12.05, 23.50),
    (S, 'EX2', I1, 10.65, 22.75, 11.20, 24.60),
    (S, 'EX2', I1, 11.20, 24.60, 12.40, 25.13),
])

try_chain('EX5tap4', [
    (S, 'EX5', I1, 13.90, 25.78, 14.35, 28.85),
    (S, 'EX5', I1, 14.35, 28.85, 11.40, 28.85),
    (V, 'EX5', 11.40, 28.85),
    (S, 'EX5', F, 11.40, 28.85, 11.20, 26.95),
])

try_chain('GPIO10v4', [
    (S, 'GPIO10', F, 8.10, 22.75, 8.55, 22.90),
    (V, 'GPIO10', 8.55, 22.90),
    (S, 'GPIO10', I1, 8.55, 22.90, 9.90, 22.80),
    (V, 'GPIO10', 9.90, 22.80),
    (S, 'GPIO10', B, 9.90, 22.80, 9.90, 22.35),
])

try_chain('GPIO1v4', [
    (S, 'GPIO1', F, 10.80, 20.20, 10.80, 21.00),
    (S, 'GPIO1', F, 10.80, 21.00, 7.20, 21.00),
    (V, 'GPIO1', 7.20, 21.00),
    (S, 'GPIO1', B, 7.20, 21.00, 7.20, 19.93),
])

try_chain('USB_B4', [
    (S, 'USB_D-', B, 6.40, 22.07, 6.42, 21.90),
    (S, 'USB_D-', B, 6.42, 21.90, 6.42, 21.55),
    (S, 'USB_D-', B, 6.42, 21.55, 7.30, 21.55),
    (V, 'USB_D-', 7.30, 21.55),
    (S, 'USB_D-', I2, 7.30, 21.55, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
