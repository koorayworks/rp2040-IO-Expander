#!/usr/bin/env python3
"""Hand-finish round 13a (redo_v13 board), 5 pairs left:
- GPIO4: U1.23 is the only orphan (J1+J2+web are one island).
  F tap north to via (8.42,15.92), I1 vertical south onto the
  web's y=23.384 horizontal
- USB_D+: J2.26 bare. B stub + via (6.0,20.9), I2 ride east,
  via (11.95,20.9), F hop onto the web seg at (12.127,19.271)
- GPIO3a: J1 island via (10.15,20.7) B ride west into the J2
  stub end (7.8,19.3), jogged around GPIO9's via (8.4,18.98)
- GPIO3b: U1 island via (8.2,15.6) I1 diagonal to via (10.15,20.7)
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

try_chain('GPIO4r13a', [
    (S, 'GPIO4', F, 8.60, 16.4635, 8.42, 15.92),
    (V, 'GPIO4', 8.42, 15.92),
    (S, 'GPIO4', I1, 8.42, 15.92, 8.42, 23.384),
])

try_chain('USBDPr13a', [
    (S, 'USB_D+', B, 6.00, 19.925, 6.00, 20.90),
    (V, 'USB_D+', 6.00, 20.90),
    (S, 'USB_D+', I2, 6.00, 20.90, 11.95, 20.90),
    (V, 'USB_D+', 11.95, 20.90),
    (S, 'USB_D+', F, 11.95, 20.90, 12.127, 19.271),
])

try_chain('GPIO3ar13a', [
    (S, 'GPIO3', B, 10.15, 20.70, 8.70, 19.60),
    (S, 'GPIO3', B, 8.70, 19.60, 7.80, 19.30),
])

try_chain('GPIO3br13a', [
    (S, 'GPIO3', I1, 8.20, 15.60, 10.15, 20.70),
])

pcbnew.SaveBoard(P, b)
print('saved')
