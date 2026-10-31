#!/usr/bin/env python3
"""Round 4 fix 9:
- GPIO0 via_bot -> (13.62,20.72): clear of GPIO7 In2 diagonal endpoint
  (13.2234,20.573) by 0.42, GPIO4 F.Cu diagonal by 0.39, C1 pad2 by
  0.36, EX6 via by 0.65, JLEG pad9 copper (disk centre (14.08,21.91))
  by 0.33 clearance. B.Cu tail and F.Cu stub adjusted.
- GND C2 track rerouted: joins the existing B.Cu GND chain segment
  (10.25,16.8828)-(10.5536,17.1864) at its midpoint (10.4018,17.0346),
  staying east/north of the EX4 B.Cu jog.
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
    ('GPIO0', L_B, (13.32, 20.35), (13.37, 20.35)),
    ('GPIO0', L_F, (13.37, 20.35), (13.3712, 20.85)),
    ('GND', L_B, (11.00, 18.35), (10.65, 17.15)),
    ('GND', L_B, (10.65, 17.15), (10.5536, 17.1864)),
]
DEL_VIA = [
    ('GPIO0', (13.37, 20.35)),
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
    ('GPIO0', L_B, (13.32, 20.35), (13.62, 20.72), 0.10),
    ('GPIO0', L_F, (13.62, 20.72), (13.3712, 20.7954), 0.10),
    ('GND', L_B, (11.00, 18.35), (10.50, 17.45), 0.20),
    ('GND', L_B, (10.50, 17.45), (10.4018, 17.0346), 0.20),
]
ADD_VIA = [
    ('GPIO0', (13.62, 20.72)),
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
