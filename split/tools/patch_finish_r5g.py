#!/usr/bin/env python3
"""Hand-finish round 5g: seventh attempts after r5f blocker map.
- EX5 tap: In1 vertical x13.90 down to (13.90,27.60) (inside J4 pin5
  rect column), via there, F west at y27.60, via (11.40,27.60), F in
- GPIO10: via (7.72,22.88) (razor pocket between GPIO12 stub end,
  GPIO4 B stub end and GPIO4 F track), In1 jog as v6
- GPIO1: F exit from pad22 SW corner (10.75,20.20), west at y20.35
- USB_D- B: south exit, west to (5.75,22.50), SW diag to via
  (5.30,23.30) outside the GPIO0 diag exclusion band, In2 east run
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

try_chain('EX5tap7', [
    (S, 'EX5', I1, 13.90, 25.78, 13.90, 27.60),
    (V, 'EX5', 13.90, 27.60),
    (S, 'EX5', F, 13.90, 27.60, 11.40, 27.60),
    (V, 'EX5', 11.40, 27.60),
    (S, 'EX5', F, 11.40, 27.60, 11.20, 26.90),
])

try_chain('GPIO10v7', [
    (S, 'GPIO10', F, 8.10, 22.75, 7.72, 22.88),
    (V, 'GPIO10', 7.72, 22.88),
    (S, 'GPIO10', I1, 7.72, 22.88, 8.60, 23.35),
    (S, 'GPIO10', I1, 8.60, 23.35, 9.90, 23.30),
    (S, 'GPIO10', I1, 9.90, 23.30, 9.90, 22.80),
    (V, 'GPIO10', 9.90, 22.80),
    (S, 'GPIO10', B, 9.90, 22.80, 9.90, 22.35),
])

try_chain('GPIO1v7', [
    (S, 'GPIO1', F, 10.75, 20.20, 10.45, 20.35),
    (S, 'GPIO1', F, 10.45, 20.35, 7.60, 20.35),
    (S, 'GPIO1', F, 7.60, 20.35, 7.20, 20.60),
    (V, 'GPIO1', 7.20, 20.60),
    (S, 'GPIO1', B, 7.20, 20.60, 7.20, 19.93),
])

try_chain('USB_B7', [
    (S, 'USB_D-', B, 6.30, 22.07, 6.30, 22.50),
    (S, 'USB_D-', B, 6.30, 22.50, 5.75, 22.50),
    (S, 'USB_D-', B, 5.75, 22.50, 5.30, 23.30),
    (V, 'USB_D-', 5.30, 23.30),
    (S, 'USB_D-', I2, 5.30, 23.30, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
