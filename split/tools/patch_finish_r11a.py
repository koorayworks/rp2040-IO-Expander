#!/usr/bin/env python3
"""Hand-finish round 11a (redo_v11 board): 6 pairs left.
- EX5: I2 diagonal from the U1-side via (6.95,18.9) to the seeded
  via (10.9,25.791) (router used I1 from the new seed via instead
  and left the U1 island hanging)
- GPIO0: J1.23 F dive to via (11.1,21.3), I1 ride west onto
  GPIO0's via (6.254,21.254)
- GPIO5: F tap off U1.24's pad south-west to via (8.75,17.58),
  B hop onto the B web's y=18.578 horizontal
- GPIO6: via at the J2 stub end (8.7,22.75), I2 ride onto the
  seeded via (9.28,20.6)
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

try_chain('EX5r11a', [
    (S, 'EX5', I2, 6.95, 18.90, 10.90, 25.791),
])

try_chain('GPIO0r11a', [
    (S, 'GPIO0', F, 11.10, 22.075, 11.10, 21.30),
    (V, 'GPIO0', 11.10, 21.30),
    (S, 'GPIO0', I1, 11.10, 21.30, 6.254, 21.254),
])

try_chain('GPIO5r11a', [
    (S, 'GPIO5', F, 9.00, 17.3635, 8.75, 17.58),
    (V, 'GPIO5', 8.75, 17.58),
    (S, 'GPIO5', B, 8.75, 17.58, 8.849, 18.578),
])

try_chain('GPIO6r11a', [
    (V, 'GPIO6', 8.70, 22.75),
    (S, 'GPIO6', I2, 8.70, 22.75, 9.28, 20.60),
])

pcbnew.SaveBoard(P, b)
print('saved')
