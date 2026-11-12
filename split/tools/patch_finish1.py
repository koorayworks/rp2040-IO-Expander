#!/usr/bin/env python3
"""Manual finish #1 on the frm7 routed module board.

Two bridges the router left open, hand-placed after corridor checks
against the routed board (segment-to-everything distance scan):
- D1 pad1 (3V3): via at (14.15,23.75) + In2 jog from the trunk's
  north rail (x 12.9) + F track into the pad's south edge.
- GPIO7: J1 pad16 and J2 pad16 sit at the same (9.0,19.925) on
  opposite faces. F/B stubs north to (9.3,19.2) + a via join them
  (the via keeps 0.11mm from GPIO9's via at (8.63,19.02)).
Also: J6 pin2 GND solid zone connection (as patch_module.py) + refill.
"""
import os, pcbnew

P = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander/split/module_board/module_board.kicad_pcb')
b = pcbnew.LoadBoard(P)

def mm(v):
    return int(round(v * 1e6))

def net(name):
    n = b.GetNetInfo().GetNetItem(name)
    assert n is not None, name
    return n

def track(x1, y1, x2, y2, layer, net_name):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(0.15))
    t.SetLayer(layer)
    t.SetNet(net(net_name))
    b.Add(t)

def via(x, y, net_name):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.45))
    v.SetDrill(mm(0.25))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net(net_name))
    b.Add(v)

F, B, I2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu
# D1 3V3 feed
via(14.15, 23.75, '3V3')
track(12.9, 23.75, 14.15, 23.75, I2, '3V3')
track(14.15, 23.75, 15.335, 23.75, F, '3V3')
# GPIO7 face-to-face join
track(9.0, 19.925, 9.0, 19.2, F, 'GPIO7')
track(9.0, 19.2, 9.3, 19.2, F, 'GPIO7')
via(9.3, 19.2, 'GPIO7')
track(9.3, 19.2, 9.0, 19.2, B, 'GPIO7')
track(9.0, 19.2, 9.0, 19.925, B, 'GPIO7')

for fp in b.GetFootprints():
    if fp.GetReference() == 'J6':
        for pad in fp.Pads():
            if str(pad.GetNumber()) == '2':
                pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print('saved', P)
