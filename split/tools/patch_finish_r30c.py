#!/usr/bin/env python3
"""Hand-finish r30c on the r30 work copy.
1) USB_D+: stitch every I2 joint (hairline gaps).
2) GPIO9: B thread W through the (8.5,19.28)/(8.35,19.15)
   needle gap to its own via (8.4,18.98).
3) GPIO1: grid-search a via + B link + F climb.
"""
import os, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checker import check_seg, check_via

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
P = os.path.join(ROOT, 'split', 'module_board', 'backup',
                 'handfinish_work.kicad_pcb')
b = pcbnew.LoadBoard(P)
mm = pcbnew.FromMM
F, B, I1, I2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu

NETS = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname():
            NETS.setdefault(n.GetNetname(), n)

def add_seg(net, layer, x1, y1, x2, y2):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(0.15)); t.SetLayer(layer); t.SetNet(NETS[net])
    b.Add(t); return t

def add_via(net, x, y, dia=0.40, drill=0.20):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(dia)); v.SetDrill(mm(drill))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F, B); v.SetNet(NETS[net])
    b.Add(v); return v

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
            added.append(add_seg(net, layer, x1, y1, x2, y2))
        else:
            _, net, x, y = st[0], st[1], st[2], st[3]
            ok, clr, worst = check_via(b, net, x, y)
            print(('PASS' if ok else 'FAIL'), f'{name} via[{net}] ({x},{y}) clr={clr:.3f} {worst}')
            if not ok:
                ok_all = False; break
            added.append(add_via(net, x, y))
    if not ok_all:
        for it in added:
            b.Remove(it)
        print(f'  -> {name} ROLLED BACK')
    else:
        print(f'  -> {name} APPLIED ({len(added)})')
    return ok_all

S = 'seg'; V = 'via'

# 1) USB_D+ stitches: small segs straddling each I2 joint
joints = [(11.068, 22.505), (9.964, 23.609), (8.210, 23.609),
          (5.875, 21.274), (5.875, 20.725)]
for (jx, jy) in joints:
    add_seg('USB_D+', I2, jx - 0.17, jy, jx + 0.17, jy)
    add_seg('USB_D+', I2, jx, jy - 0.17, jx, jy + 0.17)
print('USB_D+ stitches added (same-net, unchecked by design)')

# 2) GPIO9 thread
try_chain('GPIO9r30c', [
    (S, 'GPIO9', B, 9.60, 19.45, 9.30, 19.38),
    (S, 'GPIO9', B, 9.30, 19.38, 8.50, 19.28),
    (S, 'GPIO9', B, 8.50, 19.28, 8.35, 19.15),
    (S, 'GPIO9', B, 8.35, 19.15, 8.40, 18.98),
])

# 3) GPIO1 via grid
found = False
for vx in [6.95, 7.0, 7.05, 7.1, 7.15, 7.25, 7.3, 7.35, 7.45, 7.5, 7.55]:
    if found: break
    for vy in [18.95, 19.0, 19.05, 19.1, 19.15, 19.2, 19.3]:
        okv, clrv, wv = check_via(b, 'GPIO1', vx, vy)
        if not okv: continue
        ok1, clr1, w1 = check_seg(b, 'GPIO1', B, 7.20, 19.60, vx, vy)
        if not ok1: continue
        ok2, clr2, w2 = check_seg(b, 'GPIO1', F, vx, vy, 7.40, 18.10)
        if not ok2: continue
        print(f'GPIO1 via candidate ({vx},{vy}) via clr={clrv:.3f} B clr={clr1:.3f} F clr={clr2:.3f}')
        add_seg('GPIO1', B, 7.20, 19.60, vx, vy)
        add_via('GPIO1', vx, vy)
        add_seg('GPIO1', F, vx, vy, 7.40, 18.10)
        found = True
        break
print('GPIO1 via found:', found)

pcbnew.SaveBoard(P, b)
print('saved')
