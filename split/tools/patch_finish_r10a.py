#!/usr/bin/env python3
"""Hand-finish round 10a (redo_v10 board): 6 pairs / 5 nets left.
- EX5 tap: extend the seeded F seg INTO JP4 pad1 (edge touch at
  (10.9,26.15) did not register as connected; land at y=26.32,
  clear of the PU_EX5 neck at y=26.6)
- GPIO1: B jog from the J2 stub end to via (7.5,18.3), F hop onto
  the seeded chain end (7.4,17.95)
- GPIO3: via (8.1,18.9) + I1 ride east into the x=9.95 vertical,
  B hop onto the J2 stub
- GPIO6: J1.17 F dive via (9.5,21.5), B jog onto J2.17's stub;
  I1 vertical from the U1 via (9.4,13.75) down to (9.5,21.5)
- GPIO28: via on the I1 track end (12.5843,22.0998) (overlaps own
  J2.5 pad corner = same net), B hop onto the pad
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

try_chain('EX5r10a', [
    (S, 'EX5', F, 10.90, 26.15, 10.90, 26.32),
])

try_chain('GPIO1r10a', [
    (S, 'GPIO1', B, 7.20, 19.25, 7.50, 18.30),
    (V, 'GPIO1', 7.50, 18.30),
    (S, 'GPIO1', F, 7.50, 18.30, 7.40, 17.95),
])

try_chain('GPIO3r10a', [
    (V, 'GPIO3', 8.10, 18.90),
    (S, 'GPIO3', I1, 8.10, 18.90, 9.95, 19.60),
    (S, 'GPIO3', B, 8.10, 18.90, 7.80, 19.30),
])

try_chain('GPIO6r10a', [
    (S, 'GPIO6', F, 9.30, 22.075, 9.50, 21.50),
    (V, 'GPIO6', 9.50, 21.50),
    (S, 'GPIO6', B, 9.50, 21.50, 9.00, 21.55),
    (S, 'GPIO6', B, 9.00, 21.55, 8.70, 22.075),
    (S, 'GPIO6', I1, 9.40, 13.75, 9.50, 21.50),
])

try_chain('GPIO28r10a', [
    (V, 'GPIO28', 12.5843, 22.0998),
    (S, 'GPIO28', B, 12.5843, 22.0998, 12.30, 22.075),
])

pcbnew.SaveBoard(P, b)
print('saved')
