#!/usr/bin/env python3
"""Round 4 fix 7:
- GPIO0 v16: F.Cu west to via (13.15,16.20) (clears GPIO5 In2 diagonal
  endpoint and RESET pad1), B.Cu south-east weave east of C2 pads and
  west of GPIO2 via (12.70,17.85), down x=13.32 (clears GPIO4 via by
  0.386), jog to via_bot (13.50,21.15) (clears EX6 via by 0.55), F.Cu
  stub ending exactly on the south chain segment x=13.37.
  All prior GPIO0 surgery pieces (fix3/5/6) are removed by coordinate
  match with a full dump first.
- USB_D- v8: In2 stub to via (5.06,16.90) (clears 3V3 In2 diagonal 0.37,
  USB_VBUS B.Cu vertical x=5.42 by 0.36, BOOT pad2 0.48), F.Cu column
  x=5.12, jog to x=5.30 column (clears USB_VBUS hop via (4.94,20.6) by
  0.36), south jog west of USB_D+ via (5.5627,23.8731), into D- via
  (5.4906,24.3847).
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

print('--- GPIO0 tracks y>=12 (pre) ---')
for t in tracks:
    if t.GetNetname() == 'GPIO0':
        a, b = seg_key(t)
        if a[1] >= 12:
            print('VIA' if t.GetClass() == 'PCB_VIA' else 'L%d' % t.GetLayer(), a, b)

DEL_SEG = [
    ('GPIO0', L_F, (14.53, 16.55), (15.62, 17.20)),
    ('GPIO0', L_B, (15.62, 17.20), (15.35, 16.35)),
    ('GPIO0', L_B, (15.35, 16.35), (15.05, 13.30)),
    ('GPIO0', L_B, (15.05, 13.30), (11.60, 16.90)),
    ('GPIO0', L_B, (11.60, 16.90), (11.55, 17.85)),
    ('GPIO0', L_B, (11.55, 17.85), (12.75, 17.95)),
    ('GPIO0', L_B, (12.75, 17.95), (13.40, 18.60)),
    ('GPIO0', L_B, (13.40, 18.60), (13.40, 21.05)),
    ('GPIO0', L_F, (13.40, 21.05), (13.3712, 20.90)),
    ('GPIO0', L_F, (14.53, 16.55), (14.53, 16.90)),
    ('GPIO0', L_F, (14.53, 16.90), (12.90, 16.90)),
    ('USB_D-', L_IN2, (5.0692, 16.7004), (5.15, 16.78)),
    ('USB_D-', L_IN2, (5.15, 16.78), (5.15, 19.05)),
    ('USB_D-', L_F, (5.15, 19.05), (5.30, 19.30)),
    ('USB_D-', L_F, (5.30, 19.30), (5.30, 24.0948)),
    ('USB_D-', L_F, (5.30, 24.0948), (5.4906, 24.3847)),
]
DEL_VIA = [
    ('GPIO0', (15.62, 17.20)),
    ('GPIO0', (13.40, 21.05)),
    ('USB_D-', (5.15, 19.05)),
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
    # GPIO0 v16
    ('GPIO0', L_F, (14.53, 16.55), (13.15, 16.20), 0.10),
    ('GPIO0', L_B, (13.15, 16.20), (13.00, 17.55), 0.10),
    ('GPIO0', L_B, (13.00, 17.55), (13.25, 18.50), 0.10),
    ('GPIO0', L_B, (13.25, 18.50), (13.32, 19.11), 0.10),
    ('GPIO0', L_B, (13.32, 19.11), (13.32, 20.75), 0.10),
    ('GPIO0', L_B, (13.32, 20.75), (13.50, 21.15), 0.10),
    ('GPIO0', L_F, (13.50, 21.15), (13.37, 21.05), 0.10),
    # USB_D- v8
    ('USB_D-', L_IN2, (5.0692, 16.7004), (5.06, 16.90), 0.10),
    ('USB_D-', L_F, (5.06, 16.90), (5.12, 17.05), 0.10),
    ('USB_D-', L_F, (5.12, 17.05), (5.12, 19.15), 0.10),
    ('USB_D-', L_F, (5.12, 19.15), (5.30, 19.35), 0.10),
    ('USB_D-', L_F, (5.30, 19.35), (5.30, 23.30), 0.10),
    ('USB_D-', L_F, (5.30, 23.30), (5.15, 23.90), 0.10),
    ('USB_D-', L_F, (5.15, 23.90), (5.15, 24.3847), 0.10),
    ('USB_D-', L_F, (5.15, 24.3847), (5.4906, 24.3847), 0.10),
]
ADD_VIA = [
    ('GPIO0', (13.15, 16.20)),
    ('GPIO0', (13.50, 21.15)),
    ('USB_D-', (5.06, 16.90)),
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
