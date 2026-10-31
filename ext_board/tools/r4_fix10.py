#!/usr/bin/env python3
"""Round 4 fix 10: GND C2 stitch rerouted around the EX4 B.Cu wall
(vertical x=10.7225, y 17.51-19.78) and the EX5 via/vertical, joining
the GND via at (11.1339,19.8152) from the south-east."""
import pcbnew

IU = pcbnew.FromMM(1)
P = 'ext_board.kicad_pcb'
bd = pcbnew.LoadBoard(P)
L_B = 31
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
    ('GND', L_B, (11.75, 18.625), (11.00, 18.35)),
    ('GND', L_B, (11.00, 18.35), (10.50, 17.45)),
    ('GND', L_B, (10.50, 17.45), (10.4018, 17.0346)),
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
for t in to_remove:
    bd.Remove(t)
print('removed', len(to_remove), 'items')

def add_seg(net, layer, p1, p2, w=0.20):
    s = pcbnew.PCB_TRACK(bd)
    s.SetNet(NETC.GetNetItem(net))
    s.SetLayer(layer)
    s.SetStart(v2(*p1))
    s.SetEnd(v2(*p2))
    s.SetWidth(int(round(w * IU)))
    bd.Add(s)

ADD_SEG = [
    ('GND', L_B, (11.75, 18.625), (11.74, 19.20)),
    ('GND', L_B, (11.74, 19.20), (11.72, 19.55)),
    ('GND', L_B, (11.72, 19.55), (11.60, 20.30)),
    ('GND', L_B, (11.60, 20.30), (11.1339, 19.8152)),
]
for net, layer, p1, p2 in ADD_SEG:
    add_seg(net, layer, p1, p2)
print('added', len(ADD_SEG), 'segs')

filler = pcbnew.ZONE_FILLER(bd)
filler.Fill(bd.Zones())
bd.Save(P)
print('saved')
