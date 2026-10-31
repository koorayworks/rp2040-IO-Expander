#!/usr/bin/env python3
"""Round 4 fix 8:
- GPIO0: via_top moved to (13.22,16.15) (0.37 clear of GPIO2 In2 vertical
  x=12.85); B.Cu vertical top raised to (13.32,19.45); via_bot moved to
  (13.37,20.35) (clears C1 pad1 corner by 0.30, C1 pad2 by 0.36, GPIO4
  F.Cu diagonal by 0.354, EX6 via by 0.68, JLEG pad9 copper by 0.33);
  F.Cu stub lands on the south chain segment at (13.3712,20.85).
- GND: C2 pad2 lost its pour neighbour when the 4-pad switch (whose west
  GND pad sat next to C2) was replaced. Add an explicit B.Cu GND track
  from C2 pad2 west edge to the main-net GND via at (10.5536,17.1864),
  threading north of EX4 B.Cu vertical and west of C2.
  C1 pad2 cannot be bridged: every corridor is fenced by the USB_VBUS
  via (11.87,19.49), C1 pad1, C2 pad2, GPIO4 via and EX6 via; it stays
  a GND pour island (documented in README).
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
    ('GPIO0', L_F, (14.53, 16.55), (13.15, 16.20)),
    ('GPIO0', L_B, (13.15, 16.20), (13.00, 17.55)),
    ('GPIO0', L_B, (13.25, 18.50), (13.32, 19.11)),
    ('GPIO0', L_B, (13.32, 19.11), (13.32, 20.75)),
    ('GPIO0', L_B, (13.32, 20.75), (13.50, 21.15)),
    ('GPIO0', L_F, (13.50, 21.15), (13.37, 21.05)),
]
DEL_VIA = [
    ('GPIO0', (13.15, 16.20)),
    ('GPIO0', (13.50, 21.15)),
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
    # GPIO0 adjustments
    ('GPIO0', L_F, (14.53, 16.55), (13.22, 16.15), 0.10),
    ('GPIO0', L_B, (13.22, 16.15), (13.00, 17.55), 0.10),
    ('GPIO0', L_B, (13.25, 18.50), (13.32, 19.45), 0.10),
    ('GPIO0', L_B, (13.32, 19.45), (13.32, 20.35), 0.10),
    ('GPIO0', L_B, (13.32, 20.35), (13.37, 20.35), 0.10),
    ('GPIO0', L_F, (13.37, 20.35), (13.3712, 20.85), 0.10),
    # GND stitch for C2 pad2
    ('GND', L_B, (11.75, 18.625), (11.00, 18.35), 0.20),
    ('GND', L_B, (11.00, 18.35), (10.65, 17.15), 0.20),
    ('GND', L_B, (10.65, 17.15), (10.5536, 17.1864), 0.20),
]
ADD_VIA = [
    ('GPIO0', (13.22, 16.15)),
    ('GPIO0', (13.37, 20.35)),
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
