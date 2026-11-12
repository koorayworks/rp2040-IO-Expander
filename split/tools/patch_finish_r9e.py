#!/usr/bin/env python3
"""Hand-finish round 9e (redo_v9 board, after r9a-d rolled back):
- GPIO3 v5: F tap east off the stub end, via (8.63,17.45) between
  GPIO5's B vertical and GPIO1's chain; I2 hop to via (8.12,18.88);
  B rides to J2 stub and J1 dive via
- GPIO8 v5: via (10.5,16.25) north-east of GPIO7's I1 diagonal
- GPIO4 v6: via (8.8,15.3) north (between GPIO9's I1 vertical and
  GPIO5's F vertical end), I1 east ride then south-east onto the
  seeded I1 rail at y=23.3
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

try_chain('GPIO3r9e', [
    (S, 'GPIO3', F, 8.20, 17.3635, 8.63, 17.45),
    (V, 'GPIO3', 8.63, 17.45),
    (S, 'GPIO3', I2, 8.63, 17.45, 8.12, 18.88),
    (V, 'GPIO3', 8.12, 18.88),
    (S, 'GPIO3', B, 8.12, 18.88, 7.80, 19.30),
    (S, 'GPIO3', B, 7.80, 19.30, 8.60, 20.90),
    (S, 'GPIO3', B, 8.60, 20.90, 10.15, 20.70),
])

try_chain('GPIO8r9e', [
    (S, 'GPIO8', I2, 10.20, 15.60, 10.50, 16.25),
    (V, 'GPIO8', 10.50, 16.25),
    (S, 'GPIO8', I1, 10.50, 16.25, 10.90, 19.30),
    (V, 'GPIO8', 10.90, 19.30),
    (S, 'GPIO8', I2, 10.90, 19.30, 9.30, 21.30),
    (V, 'GPIO8', 9.30, 21.30),
    (S, 'GPIO8', B, 9.30, 21.30, 9.30, 22.075),
    (S, 'GPIO8', F, 9.30, 21.30, 8.85, 21.60),
    (S, 'GPIO8', F, 8.85, 21.60, 8.70, 22.075),
])

try_chain('GPIO4r9e', [
    (S, 'GPIO4', F, 8.60, 16.4635, 8.80, 15.30),
    (V, 'GPIO4', 8.80, 15.30),
    (S, 'GPIO4', I1, 8.80, 15.30, 11.00, 15.00),
    (S, 'GPIO4', I1, 11.00, 15.00, 11.00, 20.00),
    (S, 'GPIO4', I1, 11.00, 20.00, 9.65, 23.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
