#!/usr/bin/env python3
"""Round 4 fix 11: GND C2 stitch via In2.
Removes the fix10 B.Cu detour (collided with SJ6 pad3 / VBUS via).
Adds a GND via at (11.40,18.0328) -- exactly on the In2 GND chain
segment (10.5536,17.1864)-(12.258,18.8908) (line y=x+6.6328) -- and a
short B.Cu track from the via into C2 pad2."""
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
    ('GND', L_B, (11.75, 18.625), (11.74, 19.20)),
    ('GND', L_B, (11.74, 19.20), (11.72, 19.55)),
    ('GND', L_B, (11.72, 19.55), (11.60, 20.30)),
    ('GND', L_B, (11.60, 20.30), (11.1339, 19.8152)),
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

def add_via(net, pos):
    v = pcbnew.PCB_VIA(bd)
    v.SetNet(NETC.GetNetItem(net))
    v.SetPosition(v2(*pos))
    v.SetDrill(int(round(0.20 * IU)))
    v.SetWidth(int(round(0.40 * IU)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    bd.Add(v)

add_via('GND', (11.40, 18.0328))
add_seg('GND', L_B, (11.40, 18.0328), (11.85, 18.35))
print('added 1 via, 1 seg')

filler = pcbnew.ZONE_FILLER(bd)
filler.Fill(bd.Zones())
bd.Save(P)
print('saved')
