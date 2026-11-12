#!/usr/bin/env python3
"""Hand-finish round 5a (redo v5 board): EX2 tap, EX5 tap, GPIO10,
GPIO1, USB_D- (two gaps). Checker-verified chains; a chain applies
only if every element passes, else it rolls back."""
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

# EX2: JP3 pad1 (12.30,23.80) F -> via -> In1 endpoint (12.40,25.13)
try_chain('EX2tap', [
    (V, 'EX2', 12.55, 24.60),
    (S, 'EX2', I1, 12.55, 24.60, 12.40, 25.13),
    (S, 'EX2', F, 12.55, 24.60, 12.45, 24.20),
])

# EX5: JP4 pad1 (10.90,26.60) F -> via (11.60,25.30) -> B west run -> (13.90,25.78)
try_chain('EX5tap', [
    (S, 'EX5', B, 13.90, 25.78, 13.90, 25.30),
    (S, 'EX5', B, 13.90, 25.30, 11.60, 25.30),
    (V, 'EX5', 11.60, 25.30),
    (S, 'EX5', F, 11.60, 25.30, 11.20, 26.40),
])

# GPIO10: J1 pad13 F stub south end -> via (8.10,22.85) -> B east -> J2 pad13 rect
try_chain('GPIO10', [
    (S, 'GPIO10', F, 8.10, 22.70, 8.10, 22.85),
    (V, 'GPIO10', 8.10, 22.85),
    (S, 'GPIO10', B, 8.10, 22.85, 9.90, 22.85),
    (S, 'GPIO10', B, 9.90, 22.85, 9.90, 22.20),
])

# GPIO1: J1 pad22 F stub (10.80,19.25) -> F west -> via (7.75,19.25) -> B stub end (7.20,19.25)
try_chain('GPIO1', [
    (S, 'GPIO1', F, 10.80, 19.25, 7.75, 19.25),
    (V, 'GPIO1', 7.75, 19.25),
    (S, 'GPIO1', B, 7.75, 19.25, 7.20, 19.25),
])

# USB_D- gap A: via at island B's In2 endpoint (11.71,23.64) + In1 joiner
try_chain('USB_A', [
    (V, 'USB_D-', 11.71, 23.64),
    (S, 'USB_D-', I1, 11.71, 23.64, 11.62, 23.70),
])

# USB_D- gap B: J2 pad25 (6.30,22.075) B -> north -> east at y20.60 -> via -> F (11.35,21.30)
try_chain('USB_B', [
    (S, 'USB_D-', B, 6.30, 21.80, 6.30, 20.60),
    (S, 'USB_D-', B, 6.30, 20.60, 11.35, 20.60),
    (V, 'USB_D-', 11.35, 20.60),
    (S, 'USB_D-', F, 11.35, 20.60, 11.35, 21.30),
])

pcbnew.SaveBoard(P, b)
print('saved')
