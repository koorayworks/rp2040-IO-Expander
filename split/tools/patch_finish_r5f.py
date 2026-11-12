#!/usr/bin/env python3
"""Hand-finish round 5f: sixth attempts after r5e blocker map.
- EX2 tap: via (12.50,25.20) -- its In1 annulus covers EX2's In1
  endpoint (12.40,25.13); F north into JP3 pad1 south edge
- EX5 tap: In1 -> via (14.20,27.60) -> F west at y27.60 -> via
  (11.40,27.60) -> F into JP4 pad1
- GPIO10: via (7.70,22.88) far west, In1 south jog around GPIO6's
  via, In1 north at x9.90, via (9.90,22.80), B into J2 pad13 rect
- GPIO1: F west at y20.35, jog SW, via (7.20,20.60), B into stub
- USB_D- B: south exit x6.30 (GPIO0 diag dodged), west y22.50,
  north x5.35, via (5.35,20.75), In2 east run
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

try_chain('EX2tap6', [
    (V, 'EX2', 12.50, 25.20),
    (S, 'EX2', F, 12.50, 25.20, 12.40, 24.20),
])

try_chain('EX5tap6', [
    (S, 'EX5', I1, 13.90, 25.78, 14.20, 27.60),
    (V, 'EX5', 14.20, 27.60),
    (S, 'EX5', F, 14.20, 27.60, 11.40, 27.60),
    (V, 'EX5', 11.40, 27.60),
    (S, 'EX5', F, 11.40, 27.60, 11.20, 26.90),
])

try_chain('GPIO10v6', [
    (S, 'GPIO10', F, 8.10, 22.75, 7.70, 22.88),
    (V, 'GPIO10', 7.70, 22.88),
    (S, 'GPIO10', I1, 7.70, 22.88, 8.60, 23.35),
    (S, 'GPIO10', I1, 8.60, 23.35, 9.90, 23.30),
    (S, 'GPIO10', I1, 9.90, 23.30, 9.90, 22.80),
    (V, 'GPIO10', 9.90, 22.80),
    (S, 'GPIO10', B, 9.90, 22.80, 9.90, 22.35),
])

try_chain('GPIO1v6', [
    (S, 'GPIO1', F, 10.90, 20.20, 10.60, 20.35),
    (S, 'GPIO1', F, 10.60, 20.35, 7.60, 20.35),
    (S, 'GPIO1', F, 7.60, 20.35, 7.20, 20.60),
    (V, 'GPIO1', 7.20, 20.60),
    (S, 'GPIO1', B, 7.20, 20.60, 7.20, 19.93),
])

try_chain('USB_B6', [
    (S, 'USB_D-', B, 6.30, 22.07, 6.30, 22.50),
    (S, 'USB_D-', B, 6.30, 22.50, 5.35, 22.50),
    (S, 'USB_D-', B, 5.35, 22.50, 5.35, 20.75),
    (V, 'USB_D-', 5.35, 20.75),
    (S, 'USB_D-', I2, 5.35, 20.75, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
