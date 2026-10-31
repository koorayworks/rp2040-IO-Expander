#!/usr/bin/env python3
"""Round 4 fix 4:
- Pads 0.85 x 1.45 (1.80 height grazed GPIO4 via at (13.71,19.13)).
- BOOT: B.Cu run y~13.9 south of J4 MP pad (5.85,12.4, 1.8x2.2 -> y<=13.5),
  via2 (6.70,13.80) clear of D- In2 vertical x=5.89 and 3V3 In2 line.
- GPIO0: via_top (12.42,17.50), B.Cu path threading west of GPIO4 via and
  between C1 pads, via_bot (13.50,20.85) clear of GPIO7 In2 diagonal.
- GPIO2: In2 diagonal to via (12.70,17.85) west of RESET pad1, F.Cu column
  x=12.7 down to the south run top (12.65,19.55).
- USB_D- v5: In2 -> via (4.45,16.60) -> B.Cu south (x=4.9, bbox-safe column
  between JLEG pad13 bbox x<=4.67 and VBUS B.Cu) -> via (4.90,19.50) -> F.Cu.
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

for ref in ('SW_BOOT', 'SW_RESET'):
    fp = bd.FindFootprintByReference(ref)
    for pad in fp.Pads():
        pad.SetSize(v2(0.85, 1.45))
print('pads resized to 0.85 x 1.45')

def close(a, b):
    return abs(a[0] - b[0]) <= TOL and abs(a[1] - b[1]) <= TOL

def seg_key(t):
    s, e = t.GetStart(), t.GetEnd()
    return (s.x / IU, s.y / IU), (e.x / IU, e.y / IU)

tracks = list(bd.GetTracks())

DEL_SEG = [
    ('BOOT', L_B, (3.30, 13.90), (5.90, 13.30)),
    ('BOOT', L_F, (5.90, 13.30), (6.42, 15.20)),
    ('GPIO0', L_F, (12.90, 16.90), (12.78, 17.80)),
    ('GPIO0', L_B, (12.78, 17.80), (13.60, 19.00)),
    ('GPIO0', L_B, (13.60, 19.00), (13.55, 20.70)),
    ('GPIO0', L_F, (13.55, 20.70), (13.37, 20.80)),
    ('GPIO2', L_IN2, (12.85, 17.30), (13.10, 17.55)),
    ('GPIO2', L_IN2, (13.10, 17.55), (13.10, 19.10)),
    ('GPIO2', L_F, (13.10, 19.10), (12.45, 19.30)),
    ('GPIO2', L_F, (12.45, 19.30), (12.65, 19.55)),
    ('USB_D-', L_IN2, (4.29, 15.92), (5.95, 17.55)),
    ('USB_D-', L_F, (5.95, 17.55), (5.95, 21.30)),
    ('USB_D-', L_F, (5.95, 21.30), (5.20, 21.30)),
    ('USB_D-', L_F, (5.20, 21.30), (5.20, 24.09)),
]
DEL_VIA = [
    ('BOOT', (5.90, 13.30)),
    ('GPIO0', (12.78, 17.80)),
    ('GPIO0', (13.55, 20.70)),
    ('USB_D-', (5.95, 17.55)),
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
    # BOOT v4
    ('BOOT', L_B, (3.30, 13.90), (6.70, 13.80), 0.10),
    ('BOOT', L_F, (6.70, 13.80), (6.42, 15.20), 0.10),
    # GPIO0 v7
    ('GPIO0', L_F, (12.90, 16.90), (12.42, 17.50), 0.10),
    ('GPIO0', L_B, (12.42, 17.50), (13.45, 17.45), 0.10),
    ('GPIO0', L_B, (13.45, 17.45), (13.28, 19.60), 0.10),
    ('GPIO0', L_B, (13.28, 19.60), (13.50, 20.85), 0.10),
    ('GPIO0', L_F, (13.50, 20.85), (13.37, 20.80), 0.10),
    # GPIO2 v3
    ('GPIO2', L_IN2, (12.85, 17.30), (12.70, 17.85), 0.10),
    ('GPIO2', L_F, (12.70, 17.85), (12.70, 19.20), 0.10),
    ('GPIO2', L_F, (12.70, 19.20), (12.65, 19.55), 0.10),
    # USB_D- v5
    ('USB_D-', L_IN2, (4.29, 15.92), (4.45, 16.60), 0.10),
    ('USB_D-', L_B, (4.45, 16.60), (4.90, 17.70), 0.10),
    ('USB_D-', L_B, (4.90, 17.70), (4.90, 19.50), 0.10),
    ('USB_D-', L_F, (4.90, 19.50), (4.90, 23.90), 0.10),
    ('USB_D-', L_F, (4.90, 23.90), (5.20, 24.09), 0.10),
]
ADD_VIA = [
    ('BOOT', (6.70, 13.80)),
    ('GPIO0', (12.42, 17.50)),
    ('GPIO0', (13.50, 20.85)),
    ('GPIO2', (12.70, 17.85)),
    ('USB_D-', (4.45, 16.60)),
    ('USB_D-', (4.90, 19.50)),
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
