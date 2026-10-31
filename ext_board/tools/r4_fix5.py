#!/usr/bin/env python3
"""Round 4 fix 5 (geometry from measured pad map, south-central is empty
on B.Cu except C1/C2; SJ1/SJ2 are NOT in this area):
- GPIO0 v11: F.Cu east column to (14.53,17.60), diagonal to via (15.70,18.70)
  (In2 sum 34.40 clears GPIO6/GPIO7 diagonal pair; 0.56 from GP21 via),
  B.Cu east loop via (16.90,19.20) staying clear of J6 GP20/GP19 pads,
  via_bot (13.50,20.85).
- RESET v3: F.Cu south-edge exit to via (13.13,19.12) (clears RESET pad1,
  C1 pad1 corner, GPIO4 via, GPIO2 F column), B.Cu east run to via
  (15.60,19.60), F.Cu stub into the existing south chain at (15.39,20.12).
  Old east route and its tail segment removed.
- USB_D- v6: restore original In2 diagonal, via (5.12,16.85), F.Cu column
  x=5.12 (0.135 east of new BOOT pad2, west of D+ x=5.56), jog to the
  original x=5.2007 south column, reconnecting the kept south stub.
- Delete leftover GPIO2 via at (13.10,19.10) from fix3.
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
    ('GPIO0', L_F, (14.53, 16.55), (14.53, 16.90)),
    ('GPIO0', L_F, (14.53, 16.90), (12.90, 16.90)),
    ('GPIO0', L_F, (12.90, 16.90), (12.42, 17.50)),
    ('GPIO0', L_B, (12.42, 17.50), (13.45, 17.45)),
    ('GPIO0', L_B, (13.45, 17.45), (13.28, 19.60)),
    ('GPIO0', L_B, (13.28, 19.60), (13.50, 20.85)),
    ('GPIO0', L_F, (13.50, 20.85), (13.37, 20.80)),
    ('RESET', L_F, (13.90, 18.05), (14.88, 18.35)),
    ('RESET', L_F, (14.88, 18.35), (14.88, 19.62)),
    ('RESET', L_F, (14.88, 19.62), (15.39, 20.12)),
    ('USB_D-', L_IN2, (4.2925, 15.9237), (4.45, 16.60)),
    ('USB_D-', L_B, (4.45, 16.60), (4.90, 17.70)),
    ('USB_D-', L_B, (4.90, 17.70), (4.90, 19.50)),
    ('USB_D-', L_F, (4.90, 19.50), (4.90, 23.90)),
    ('USB_D-', L_F, (4.90, 23.90), (5.20, 24.09)),
]
DEL_VIA = [
    ('GPIO0', (12.42, 17.50)),
    ('GPIO0', (13.50, 20.85)),
    ('GPIO2', (13.10, 19.10)),
    ('USB_D-', (4.45, 16.60)),
    ('USB_D-', (4.90, 19.50)),
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
    # GPIO0 v11
    ('GPIO0', L_F, (14.53, 16.55), (14.53, 17.60), 0.10),
    ('GPIO0', L_F, (14.53, 17.60), (15.70, 18.70), 0.10),
    ('GPIO0', L_B, (15.70, 18.70), (16.90, 19.20), 0.10),
    ('GPIO0', L_B, (16.90, 19.20), (14.45, 20.75), 0.10),
    ('GPIO0', L_B, (14.45, 20.75), (13.50, 20.85), 0.10),
    ('GPIO0', L_F, (13.50, 20.85), (13.37, 20.80), 0.10),
    # RESET v3
    ('RESET', L_F, (13.35, 18.81), (13.13, 19.12), 0.10),
    ('RESET', L_B, (13.13, 19.12), (14.60, 19.22), 0.10),
    ('RESET', L_B, (14.60, 19.22), (15.60, 19.60), 0.10),
    ('RESET', L_F, (15.60, 19.60), (15.39, 20.12), 0.10),
    # USB_D- v6
    ('USB_D-', L_IN2, (4.2925, 15.9237), (5.0692, 16.7004), 0.10),
    ('USB_D-', L_IN2, (5.0692, 16.7004), (5.12, 16.85), 0.10),
    ('USB_D-', L_F, (5.12, 16.85), (5.12, 19.15), 0.10),
    ('USB_D-', L_F, (5.12, 19.15), (5.2007, 19.30), 0.10),
    ('USB_D-', L_F, (5.2007, 19.30), (5.2007, 24.0948), 0.10),
]
ADD_VIA = [
    ('GPIO0', (15.70, 18.70)),
    ('GPIO0', (13.50, 20.85)),
    ('RESET', (13.13, 19.12)),
    ('RESET', (15.60, 19.60)),
    ('USB_D-', (5.12, 16.85)),
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
