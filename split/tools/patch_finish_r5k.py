#!/usr/bin/env python3
"""Hand-finish round 5k: eleventh attempts after r5j blocker map.
- GPIO10: F south exit under the stub, west+north jog to via
  (7.55,22.90), B two-seg hop over GPIO4's B stub into J2 pad13
- GPIO1: F west run at y17.95 lands directly on U1 pin20's own
  stub (7.40,17.36-18.10) -- no via needed
- USB_D- B: thread x6.42 north to (6.42,21.42), via there
  (GPIO12 via dodged at 0.567), In1 diag east into island A's
  own In1 segment endpoint zone (11.58,23.62)
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

try_chain('GPIO10v11', [
    (S, 'GPIO10', F, 8.10, 22.75, 8.10, 23.02),
    (S, 'GPIO10', F, 8.10, 23.02, 7.55, 22.90),
    (V, 'GPIO10', 7.55, 22.90),
    (S, 'GPIO10', B, 7.55, 22.90, 8.60, 23.20),
    (S, 'GPIO10', B, 8.60, 23.20, 9.90, 22.35),
])

try_chain('GPIO1v11', [
    (S, 'GPIO1', F, 10.80, 19.60, 10.65, 18.90),
    (S, 'GPIO1', F, 10.65, 18.90, 10.30, 17.95),
    (S, 'GPIO1', F, 10.30, 17.95, 7.40, 17.95),
])

try_chain('USB_B11', [
    (S, 'USB_D-', B, 6.40, 22.07, 6.42, 21.90),
    (S, 'USB_D-', B, 6.42, 21.90, 6.42, 21.42),
    (V, 'USB_D-', 6.42, 21.42),
    (S, 'USB_D-', I1, 6.42, 21.42, 11.58, 23.62),
])

pcbnew.SaveBoard(P, b)
print('saved')
