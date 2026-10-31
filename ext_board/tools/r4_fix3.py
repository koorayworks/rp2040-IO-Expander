#!/usr/bin/env python3
"""Round 4 fix 3:
- Resize switch pads to 0.85 (X) x 1.80 (Y): datasheet pattern 1.80(X) x 1.35(Y)
  cannot fit: BOOT pad1 vs USB_VBUS F track (x=5.3) needs width <=1.28;
  RESET pad1 vs GP22 via (14.2625,18.5694) needs width <=0.90. Narrow across,
  lengthen along axis to keep solder area.
- BOOT: NW via + B.Cu run north of TB3 line + via east of D+ barrier.
- GPIO0: F west along y=16.90 (between the two RESET pads), via west of pad1,
  B.Cu diagonal south between C1 pads, via bottom east of EX6 via, join chain.
- GPIO2: In2 vertical x=13.10 west of pad1, via, F stub to south run top.
- USB_D-: single via at (5.95,17.55), F.Cu run south, jog west at y=21.30
  (between JLEG pad12/pad13 copper), south on the original x=5.20 path.
- Delete dangling VBUS F stub and leftover D- stub from fix2.
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

# --- resize pads ---
for ref in ('SW_BOOT', 'SW_RESET'):
    fp = bd.FindFootprintByReference(ref)
    for pad in fp.Pads():
        pad.SetSize(v2(0.85, 1.80))
        pp = pad.GetPosition()
        print(ref, 'pad', pad.GetNumber(), pad.GetNetname(),
              'board (%.3f, %.3f) size (%.2f, %.2f)' % (
                  pp.x / IU, pp.y / IU,
                  pad.GetSize().x / IU, pad.GetSize().y / IU))

def close(a, b):
    return abs(a[0] - b[0]) <= TOL and abs(a[1] - b[1]) <= TOL

def seg_key(t):
    s, e = t.GetStart(), t.GetEnd()
    return (s.x / IU, s.y / IU), (e.x / IU, e.y / IU)

tracks = list(bd.GetTracks())

DEL_SEG = [
    # fix2 BOOT hop
    ('BOOT', L_F, (5.00, 14.40), (5.00, 15.20)),
    ('BOOT', L_B, (5.00, 15.20), (6.42, 15.20)),
    # fix2 GPIO0 east/In2 attempt
    ('GPIO0', L_F, (14.53, 16.55), (15.62, 17.50)),
    ('GPIO0', L_F, (15.62, 17.50), (15.62, 17.85)),
    ('GPIO0', L_IN2, (15.62, 17.85), (15.50, 18.70)),
    ('GPIO0', L_IN2, (15.50, 18.70), (14.60, 19.15)),
    ('GPIO0', L_IN2, (14.60, 19.15), (13.40, 20.20)),
    ('GPIO0', L_F, (13.40, 20.20), (13.37, 20.80)),
    # fix2 GPIO2 west detour (all of it)
    ('GPIO2', L_F, (12.30, 18.55), (12.30, 17.20)),
    ('GPIO2', L_F, (12.30, 17.20), (11.90, 16.30)),
    ('GPIO2', L_F, (11.90, 16.30), (10.80, 16.00)),
    ('GPIO2', L_B, (10.80, 16.00), (10.80, 19.85)),
    ('GPIO2', L_B, (10.80, 19.85), (11.20, 19.85)),
    ('GPIO2', L_IN2, (11.20, 19.85), (12.60, 20.20)),
    ('GPIO2', L_IN2, (12.60, 20.20), (12.75, 20.55)),
    ('GPIO2', L_IN2, (12.75, 20.55), (13.60, 20.55)),
    ('GPIO2', L_IN2, (13.60, 20.55), (13.60, 19.60)),
    ('GPIO2', L_IN2, (13.60, 19.60), (12.95, 19.60)),
    ('GPIO2', L_IN2, (12.95, 19.60), (12.95, 17.45)),
    ('GPIO2', L_IN2, (12.95, 17.45), (12.85, 17.30)),
    ('GPIO2', L_F, (12.30, 18.55), (12.45, 19.30)),
    # fix2 USB_D-
    ('USB_D-', L_IN2, (4.29, 15.92), (5.85, 17.70)),
    ('USB_D-', L_F, (5.85, 17.70), (5.85, 20.35)),
    ('USB_D-', L_IN2, (5.85, 20.35), (5.15, 20.45)),
    ('USB_D-', L_F, (5.15, 20.45), (5.15, 23.90)),
    ('USB_D-', L_F, (5.15, 23.90), (5.20, 24.09)),
    ('USB_D-', L_F, (6.05, 17.90), (5.98, 18.50)),
    # dangling VBUS stub (left by round-4 surgery)
    ('USB_VBUS', L_F, (5.30, 15.58), (4.72, 16.16)),
]
DEL_VIA = [
    ('BOOT', (5.00, 15.20)),
    ('BOOT', (6.42, 15.20)),
    ('GPIO0', (15.62, 17.85)),
    ('GPIO0', (13.40, 20.20)),
    ('GPIO2', (10.80, 16.00)),
    ('GPIO2', (11.20, 19.85)),
    ('USB_D-', (5.85, 17.70)),
    ('USB_D-', (5.85, 20.35)),
    ('USB_D-', (5.15, 20.45)),
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
    # BOOT v3
    ('BOOT', L_F, (4.20, 13.90), (3.30, 13.90), 0.10),
    ('BOOT', L_B, (3.30, 13.90), (5.90, 13.30), 0.10),
    ('BOOT', L_F, (5.90, 13.30), (6.42, 15.20), 0.10),
    # GPIO0 v6 (F west + B.Cu south)
    ('GPIO0', L_F, (14.53, 16.55), (14.53, 16.90), 0.10),
    ('GPIO0', L_F, (14.53, 16.90), (12.90, 16.90), 0.10),
    ('GPIO0', L_F, (12.90, 16.90), (12.78, 17.80), 0.10),
    ('GPIO0', L_B, (12.78, 17.80), (13.60, 19.00), 0.10),
    ('GPIO0', L_B, (13.60, 19.00), (13.55, 20.70), 0.10),
    ('GPIO0', L_F, (13.55, 20.70), (13.37, 20.80), 0.10),
    # GPIO2 final (In2 west of RESET pad1)
    ('GPIO2', L_IN2, (12.85, 17.30), (13.10, 17.55), 0.10),
    ('GPIO2', L_IN2, (13.10, 17.55), (13.10, 19.10), 0.10),
    ('GPIO2', L_F, (13.10, 19.10), (12.45, 19.30), 0.10),
    # USB_D- v4
    ('USB_D-', L_IN2, (4.29, 15.92), (5.95, 17.55), 0.10),
    ('USB_D-', L_F, (5.95, 17.55), (5.95, 21.30), 0.10),
    ('USB_D-', L_F, (5.95, 21.30), (5.20, 21.30), 0.10),
    ('USB_D-', L_F, (5.20, 21.30), (5.20, 24.09), 0.10),
]
ADD_VIA = [
    ('BOOT', (3.30, 13.90)),
    ('BOOT', (5.90, 13.30)),
    ('GPIO0', (12.78, 17.80)),
    ('GPIO0', (13.55, 20.70)),
    ('GPIO2', (13.10, 19.10)),
    ('USB_D-', (5.95, 17.55)),
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
