#!/usr/bin/env python3
"""Hand-finish round 5m:
- GPIO1: jog south then along the GPIO7/GPIO3 via bisector to
  (9.89,18.23), west into U1 pin20's stub at y17.95
- USB_D- B: south exit, west at y22.35 (GPIO28 via dodged),
  jog NW, north at x5.38 west of J2 pad27 rect, via (5.38,21.00),
  In2 east run to island B endpoint (11.35,21.30)
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

try_chain('GPIO1v13', [
    (S, 'GPIO1', F, 10.80, 19.60, 10.65, 18.90),
    (S, 'GPIO1', F, 10.65, 18.90, 10.43, 19.07),
    (S, 'GPIO1', F, 10.43, 19.07, 9.89, 18.23),
    (S, 'GPIO1', F, 9.89, 18.23, 7.40, 17.95),
])

try_chain('USB_B13', [
    (S, 'USB_D-', B, 6.30, 22.07, 6.30, 22.35),
    (S, 'USB_D-', B, 6.30, 22.35, 5.68, 22.35),
    (S, 'USB_D-', B, 5.68, 22.35, 5.38, 22.20),
    (S, 'USB_D-', B, 5.38, 22.20, 5.38, 21.00),
    (V, 'USB_D-', 5.38, 21.00),
    (S, 'USB_D-', I2, 5.38, 21.00, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
