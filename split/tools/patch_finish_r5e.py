#!/usr/bin/env python3
"""Hand-finish round 5e: fifth attempts after r5d blocker map.
- EX2 tap: via (13.90,24.45) SE pocket, F into JP3 pad1 SE corner,
  In1 two-seg hop north of VSYS endpoint joining EX2's In1 diag zone
- EX5 tap: In1 diag shifted west to (14.05,28.85) dodging 3V3 via
- GPIO10: via (8.25,22.90) west of GPIO6's B stub
- GPIO1: F SE exit from pad22, west at y21.30 (GPIO6 via dodged)
- USB_D- B: south exit, west at y22.60, north at x5.35 around the
  GND diag's west end, via (5.35,20.75), long In2 run east
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

try_chain('EX2tap5', [
    (V, 'EX2', 13.90, 24.45),
    (S, 'EX2', F, 13.90, 24.45, 12.60, 24.22),
    (S, 'EX2', I1, 13.90, 24.45, 13.60, 24.10),
    (S, 'EX2', I1, 13.60, 24.10, 12.40, 25.13),
])

try_chain('EX5tap5', [
    (S, 'EX5', I1, 13.90, 25.78, 14.05, 28.85),
    (S, 'EX5', I1, 14.05, 28.85, 11.40, 28.85),
    (V, 'EX5', 11.40, 28.85),
    (S, 'EX5', F, 11.40, 28.85, 11.20, 26.95),
])

try_chain('GPIO10v5', [
    (S, 'GPIO10', F, 8.10, 22.75, 8.25, 22.90),
    (V, 'GPIO10', 8.25, 22.90),
    (S, 'GPIO10', I1, 8.25, 22.90, 9.90, 22.80),
    (V, 'GPIO10', 9.90, 22.80),
    (S, 'GPIO10', B, 9.90, 22.80, 9.90, 22.35),
])

try_chain('GPIO1v5', [
    (S, 'GPIO1', F, 10.90, 20.20, 11.30, 21.30),
    (S, 'GPIO1', F, 11.30, 21.30, 7.20, 21.30),
    (V, 'GPIO1', 7.20, 21.30),
    (S, 'GPIO1', B, 7.20, 21.30, 7.20, 19.93),
])

try_chain('USB_B5', [
    (S, 'USB_D-', B, 6.40, 22.07, 6.40, 22.60),
    (S, 'USB_D-', B, 6.40, 22.60, 5.35, 22.60),
    (S, 'USB_D-', B, 5.35, 22.60, 5.35, 20.75),
    (V, 'USB_D-', 5.35, 20.75),
    (S, 'USB_D-', I2, 5.35, 20.75, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
