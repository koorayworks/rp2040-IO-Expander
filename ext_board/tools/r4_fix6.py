#!/usr/bin/env python3
"""Round 4 fix 6 (based on measured effective pad shapes: JLEG copper is
offset east, west edge x=15.87 for side pads):
- RESET v6: pure F.Cu. East run at y~18.2 north of GP22 via, then restore
  the original R3 corridor (15.371,18.662)->(15.678,18.969)->x=15.667->
  (15.392,20.119) into the kept south chain.
- GPIO0 v14: F.Cu to via (15.62,17.20) (clears GP21 B.Cu vertical x=15.269
  by 0.351, GPIO6 In2 diagonal, JLEG pad6 copper), B.Cu north-west loop
  west of GP24 vertical (x=14.757) and west of C2, down the C1 gap column
  x=13.40, via_bot (13.40,21.05), F.Cu stub into the south chain.
- USB_D- v7: In2 stub x=5.15 south to via (5.15,19.05) (clears new BOOT
  pad2 and D+ column), F.Cu jog to x=5.30 south column (clears the R4
  USB_VBUS hop via at (4.94,20.6)), reconnect to the south via.
"""
import pcbnew

IU = pcbnew.FromMM(1)
P = 'ext_board.kicad_pcb'
bd = pcbnew.LoadBoard(P)
L_F, L_IN2, L_B = 0, 2, 31
NETC = bd.GetNetInfo()
TOL = 0.06

def v2(x, y):
    return pcbnew.VECTOR2I(int(round(x * IU)), int(round(y * IU)))

def close(a, b):
    return abs(a[0] - b[0]) <= TOL and abs(a[1] - b[1]) <= TOL

def seg_key(t):
    s, e = t.GetStart(), t.GetEnd()
    return (s.x / IU, s.y / IU), (e.x / IU, e.y / IU)

tracks = list(bd.GetTracks())

DEL_SEG = [
    # GPIO0 fix5 + fix3 pieces
    ('GPIO0', L_F, (14.53, 16.55), (14.53, 17.60)),
    ('GPIO0', L_F, (14.53, 17.60), (15.70, 18.70)),
    ('GPIO0', L_B, (15.70, 18.70), (16.90, 19.20)),
    ('GPIO0', L_B, (16.90, 19.20), (14.45, 20.75)),
    ('GPIO0', L_B, (14.45, 20.75), (13.50, 20.85)),
    ('GPIO0', L_F, (13.50, 20.85), (13.37, 20.80)),
    ('GPIO0', L_F, (14.53, 16.55), (14.53, 16.90)),
    ('GPIO0', L_F, (14.53, 16.90), (12.90, 16.90)),
    # RESET fix5 pieces
    ('RESET', L_F, (13.35, 18.81), (13.13, 19.12)),
    ('RESET', L_B, (13.13, 19.12), (14.60, 19.22)),
    ('RESET', L_B, (14.60, 19.22), (15.60, 19.60)),
    ('RESET', L_F, (15.60, 19.60), (15.39, 20.12)),
    # USB_D- fix5 pieces
    ('USB_D-', L_IN2, (5.0692, 16.7004), (5.12, 16.85)),
    ('USB_D-', L_F, (5.12, 16.85), (5.12, 19.15)),
    ('USB_D-', L_F, (5.12, 19.15), (5.2007, 19.30)),
    ('USB_D-', L_F, (5.2007, 19.30), (5.2007, 24.0948)),
    ('USB_D-', L_F, (5.2007, 24.0948), (5.4906, 24.3847)),
]
DEL_VIA = [
    ('GPIO0', (15.70, 18.70)),
    ('GPIO0', (13.50, 20.85)),
    ('RESET', (13.13, 19.12)),
    ('RESET', (15.60, 19.60)),
    ('USB_D-', (5.12, 16.85)),
]

to_remove = []
for net, layer, p1, p2 in DEL_SEG:
    hit = None
    for t in tracks:
        if t.GetClass() == 'PCB_VIA' or t in to_remove:
            continue
        if t.GetNetname() != net or t.GetLayer() != layer:
            continue
        a, b = seg_key(t)
        if (close(a, p1) and close(b, p2)) or (close(a, p2) and close(b, p1)):
            hit = t
            break
    if hit is None:
        print('WARN seg not found:', net, layer, p1, p2)
    else:
        to_remove.append(hit)
for net, pos in DEL_VIA:
    hit = None
    for t in tracks:
        if t.GetClass() != 'PCB_VIA' or t in to_remove:
            continue
        if t.GetNetname() != net:
            continue
        s = t.GetStart()
        if close((s.x / IU, s.y / IU), pos):
            hit = t
            break
    if hit is None:
        print('WARN via not found:', net, pos)
    else:
        to_remove.append(hit)
for t in to_remove:
    bd.Remove(t)
print('removed', len(to_remove), 'items')

def add_seg(net, layer, p1, p2, w=0.10):
    s = pcbnew.PCB_TRACK(bd)
    s.SetNet(NETC.GetNetItem(net))
    s.SetLayer(layer)
    s.SetStart(v2(*p1))
    s.SetEnd(v2(*p2))
    s.SetWidth(int(round(w * IU)))
    bd.Add(s)

def add_via(net, pos):
    v = pcbnew.PCB_VIA(bd)
    v.SetNet(NETC.GetNetItem(net))
    v.SetPosition(v2(*pos))
    v.SetDrill(int(round(0.20 * IU)))
    v.SetWidth(int(round(0.40 * IU)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    bd.Add(v)

ADD_SEG = [
    # GPIO0 v14
    ('GPIO0', L_F, (14.53, 16.55), (15.62, 17.20), 0.10),
    ('GPIO0', L_B, (15.62, 17.20), (15.35, 16.35), 0.10),
    ('GPIO0', L_B, (15.35, 16.35), (15.05, 13.30), 0.10),
    ('GPIO0', L_B, (15.05, 13.30), (11.60, 16.90), 0.10),
    ('GPIO0', L_B, (11.60, 16.90), (11.55, 17.85), 0.10),
    ('GPIO0', L_B, (11.55, 17.85), (12.75, 17.95), 0.10),
    ('GPIO0', L_B, (12.75, 17.95), (13.40, 18.60), 0.10),
    ('GPIO0', L_B, (13.40, 18.60), (13.40, 21.05), 0.10),
    ('GPIO0', L_F, (13.40, 21.05), (13.3712, 20.90), 0.10),
    # RESET v6
    ('RESET', L_F, (13.935, 18.15), (14.90, 18.20), 0.10),
    ('RESET', L_F, (14.90, 18.20), (15.371, 18.662), 0.10),
    ('RESET', L_F, (15.371, 18.662), (15.678, 18.969), 0.10),
    ('RESET', L_F, (15.678, 18.969), (15.678, 19.111), 0.10),
    ('RESET', L_F, (15.678, 19.111), (15.667, 19.122), 0.10),
    ('RESET', L_F, (15.667, 19.122), (15.667, 19.845), 0.10),
    ('RESET', L_F, (15.667, 19.845), (15.392, 20.119), 0.10),
    # USB_D- v7
    ('USB_D-', L_IN2, (5.0692, 16.7004), (5.15, 16.78), 0.10),
    ('USB_D-', L_IN2, (5.15, 16.78), (5.15, 19.05), 0.10),
    ('USB_D-', L_F, (5.15, 19.05), (5.30, 19.30), 0.10),
    ('USB_D-', L_F, (5.30, 19.30), (5.30, 24.0948), 0.10),
    ('USB_D-', L_F, (5.30, 24.0948), (5.4906, 24.3847), 0.10),
]
ADD_VIA = [
    ('GPIO0', (15.62, 17.20)),
    ('GPIO0', (13.40, 21.05)),
    ('USB_D-', (5.15, 19.05)),
]
for net, layer, p1, p2, w in ADD_SEG:
    add_seg(net, layer, p1, p2, w)
for net, pos in ADD_VIA:
    add_via(net, pos)
print('added', len(ADD_SEG), 'segs,', len(ADD_VIA), 'vias')

filler = pcbnew.ZONE_FILLER(bd)
filler.Fill(bd.Zones())
bd.Save(P)
print('saved')
