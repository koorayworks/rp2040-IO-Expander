#!/usr/bin/env python3
"""Round 4 fix 2: local re-routing after switch swap.
BOOT: B.Cu hop over the F.Cu VBUS/D+ barrier. RESET: signal pad now at bottom
(after 180deg rotation) -> short east column; GND pad top -> stub to via
(13.3,13.0). GPIO0: east-side In2 descent + restored original south chain.
GPIO2: west via + B.Cu south + In2 return east of TB5 wall. USB_D-: via moved
west off EX1 B.Cu, In2 hop over JLEG pad12. TB3: via shifted east off GPIO29."""
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

tracks = list(bd.GetTracks())  # cache once (accessor degrades after edits)

DEL_SEG = [
    ('BOOT', L_F, (4.51, 13.935), (6.42, 13.935)),
    ('BOOT', L_F, (6.42, 13.935), (6.42, 18.66)),
    ('RESET', L_F, (13.51, 13.935), (15.25, 14.27)),
    ('RESET', L_F, (14.88, 14.27), (15.25, 14.27)),
    ('RESET', L_F, (14.88, 14.27), (14.88, 19.62)),
    ('RESET', L_F, (14.88, 19.62), (15.39, 20.12)),
    ('GND', L_F, (12.62, 16.98), (12.95, 17.75)),
    ('GPIO0', L_F, (14.53, 16.55), (11.95, 16.55)),
    ('GPIO0', L_F, (11.95, 16.55), (11.95, 19.75)),
    ('GPIO0', L_F, (11.95, 19.75), (11.80, 20.65)),
    ('GPIO0', L_B, (11.80, 20.65), (11.80, 23.50)),
    ('GPIO0', L_B, (11.80, 23.50), (13.30, 23.50)),
    ('GPIO2', L_IN2, (12.85, 17.30), (12.31, 17.50)),
    ('GPIO2', L_F, (12.31, 17.50), (12.30, 18.55)),
    ('USB_D-', L_IN2, (4.29, 15.92), (6.05, 17.90)),
    ('USB_D-', L_F, (5.98, 18.50), (5.98, 23.60)),
    ('USB_D-', L_F, (5.98, 23.60), (5.20, 24.09)),
    ('TB3', L_F, (3.16, 14.70), (3.16, 18.94)),
    ('TB3', L_B, (4.49, 14.64), (3.16, 14.70)),
]
DEL_VIA = [
    ('GND', (12.62, 16.98)),
    ('GPIO0', (11.80, 20.65)),
    ('GPIO0', (13.30, 23.50)),
    ('GPIO2', (12.31, 17.50)),
    ('USB_D-', (6.05, 17.90)),
    ('TB3', (3.16, 14.70)),
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
    # BOOT: F stub -> via -> B.Cu east -> via -> F column (joins 18.66 tail)
    ('BOOT', L_F, (5.00, 14.40), (5.00, 15.20), 0.10),
    ('BOOT', L_B, (5.00, 15.20), (6.42, 15.20), 0.10),
    ('BOOT', L_F, (6.42, 15.20), (6.42, 18.66), 0.10),
    # RESET: bottom pad east -> column -> tail
    ('RESET', L_F, (13.90, 18.05), (14.88, 18.35), 0.10),
    ('RESET', L_F, (14.88, 18.35), (14.88, 19.62), 0.10),
    ('RESET', L_F, (14.88, 19.62), (15.39, 20.12), 0.10),
    # RESET GND top pad -> existing GND via (13.3,13.0)
    ('GND', L_F, (13.45, 13.30), (13.30, 13.00), 0.20),
    # GPIO0: east F -> via -> In2 descent -> via -> restored chain
    ('GPIO0', L_F, (14.53, 16.55), (15.62, 17.50), 0.10),
    ('GPIO0', L_F, (15.62, 17.50), (15.62, 17.85), 0.10),
    ('GPIO0', L_IN2, (15.62, 17.85), (15.50, 18.70), 0.10),
    ('GPIO0', L_IN2, (15.50, 18.70), (14.60, 19.15), 0.10),
    ('GPIO0', L_IN2, (14.60, 19.15), (13.40, 20.20), 0.10),
    ('GPIO0', L_F, (13.40, 20.20), (13.37, 20.80), 0.10),
    ('GPIO0', L_F, (13.37, 20.80), (13.37, 21.13), 0.10),
    ('GPIO0', L_F, (13.37, 21.13), (13.16, 21.34), 0.10),
    ('GPIO0', L_F, (13.16, 21.34), (13.16, 23.36), 0.10),
    # GPIO2: F north-west -> via -> B.Cu south -> via -> In2 return
    ('GPIO2', L_F, (12.30, 18.55), (12.30, 17.20), 0.10),
    ('GPIO2', L_F, (12.30, 17.20), (11.90, 16.30), 0.10),
    ('GPIO2', L_F, (11.90, 16.30), (10.80, 16.00), 0.10),
    ('GPIO2', L_B, (10.80, 16.00), (10.80, 19.85), 0.10),
    ('GPIO2', L_B, (10.80, 19.85), (11.20, 19.85), 0.10),
    ('GPIO2', L_IN2, (11.20, 19.85), (12.60, 20.20), 0.10),
    ('GPIO2', L_IN2, (12.60, 20.20), (12.75, 20.55), 0.10),
    ('GPIO2', L_IN2, (12.75, 20.55), (13.60, 20.55), 0.10),
    ('GPIO2', L_IN2, (13.60, 20.55), (13.60, 19.60), 0.10),
    ('GPIO2', L_IN2, (13.60, 19.60), (12.95, 19.60), 0.10),
    ('GPIO2', L_IN2, (12.95, 19.60), (12.95, 17.45), 0.10),
    ('GPIO2', L_IN2, (12.95, 17.45), (12.85, 17.30), 0.10),
    # USB_D-: via west -> F south -> via -> In2 west -> via -> F south (old path)
    ('USB_D-', L_IN2, (4.29, 15.92), (5.85, 17.70), 0.10),
    ('USB_D-', L_F, (5.85, 17.70), (5.85, 20.35), 0.10),
    ('USB_D-', L_IN2, (5.85, 20.35), (5.15, 20.45), 0.10),
    ('USB_D-', L_F, (5.15, 20.45), (5.15, 23.90), 0.10),
    ('USB_D-', L_F, (5.15, 23.90), (5.20, 24.09), 0.10),
    # TB3: via shifted east, F stub down to column
    ('TB3', L_F, (3.30, 14.60), (3.16, 15.20), 0.10),
    ('TB3', L_F, (3.16, 15.20), (3.16, 18.94), 0.10),
    ('TB3', L_B, (4.49, 14.64), (3.30, 14.60), 0.10),
]
ADD_VIA = [
    ('BOOT', (5.00, 15.20)),
    ('BOOT', (6.42, 15.20)),
    ('GPIO0', (15.62, 17.85)),
    ('GPIO0', (13.40, 20.20)),
    ('GPIO2', (10.80, 16.00)),
    ('GPIO2', (11.20, 19.85)),
    ('USB_D-', (5.85, 17.70)),
    ('USB_D-', (5.85, 20.35)),
    ('USB_D-', (5.15, 20.45)),
    ('TB3', (3.30, 14.60)),
]
for net, layer, p1, p2, w in ADD_SEG:
    add_seg(net, layer, p1, p2, w)
for net, pos in ADD_VIA:
    add_via(net, pos)
print('added', len(ADD_SEG), 'segs,', len(ADD_VIA), 'vias')

# refill zones
filler = pcbnew.ZONE_FILLER(bd)
filler.Fill(bd.Zones())
bd.Save(P)
print('saved')
