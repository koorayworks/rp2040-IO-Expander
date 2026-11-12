#!/usr/bin/env python3
"""Hand-finish round 16a (redo_v16 board, 0.40-via round), 3 pairs:
- GPIO3: J2 stub is the only orphan (U1+J1 joined by the B web).
  B ride (7.8,19.3)->(9.05,19.55)->(9.9,19.5) onto the web's
  x=9.9 vertical, jogged around GPIO9's via (8.4,18.98)
- GPIO0: J2.23 bare. B stub + via (6.9,22.75), I1 diagonal onto
  the web via point (11.6,20.85)
- GPIO4: U1.23 bare. F stub + 0.40 via (8.6,15.95) (fits with
  0.40 vias: 0.532 from GPIO3's via, 0.378 from GPIO5's ride),
  I1 vertical south onto the web's y=23.373 horizontal
Checker evaluates candidate vias at 0.45 dia (conservative);
the GPIO4 via is placed at 0.40/0.20 to match round 16.
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
            _, net, x, y = st[0], st[1], st[2], st[3]
            dia, drill = (st[4], st[5]) if len(st) > 4 else (0.45, 0.25)
            ok, clr, worst = check_via(b, net, x, y)
            print(('PASS' if ok else 'FAIL'), f'{name} via[{net}] ({x},{y}) clr={clr:.3f} {worst}')
            if not ok:
                ok_all = False; break
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetWidth(mm(dia)); v.SetDrill(mm(drill))
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

try_chain('GPIO3r16a', [
    (S, 'GPIO3', B, 7.80, 19.30, 9.05, 19.55),
    (S, 'GPIO3', B, 9.05, 19.55, 9.90, 19.50),
])

try_chain('GPIO0r16a', [
    (S, 'GPIO0', B, 6.90, 22.075, 6.90, 22.75),
    (V, 'GPIO0', 6.90, 22.75),
    (S, 'GPIO0', I1, 6.90, 22.75, 11.60, 20.85),
])

try_chain('GPIO4r16a', [
    (S, 'GPIO4', F, 8.60, 16.4635, 8.60, 15.95),
    (V, 'GPIO4', 8.60, 15.95, 0.40, 0.20),
    (S, 'GPIO4', I1, 8.60, 15.95, 8.60, 23.373),
])

pcbnew.SaveBoard(P, b)
print('saved')
