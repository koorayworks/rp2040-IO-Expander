#!/usr/bin/env python3
"""Post-route patches for the Zero-side board (fr11+ no-plane routes).

Routing history: with the GND zone exported as a Specctra plane,
Freerouting either stranded GND islands (fr8, zone fragmentation) or
treated B.Cu as plane-only (fr10). Since fr11 the DSN is exported
WITHOUT the zone (tools/route_prep_noplane.py), so the router wires
GND as an ordinary net and no hand bridges are needed. build_board.py
pre-routes stubs for the two fanouts the router cannot start
(USB_D- at J3-25, STATUS_LED at D1-4) and shrinks U1's pads.

What remains here:
1. U1 (USBLC6) pads -> 0.90x0.60 (idempotent safety net; the library
   1.32mm pads put pad6 0.011mm from J2's shell pad S1).
2. Solid zone connection for the three PTH GND pads whose In1 thermal
   relief otherwise gets only 1 spoke (starved_thermal): J1 pad2
   (1.68,4.13) and J2 shell pads S1 (4.68,5.82) / (13.32,5.82).
Usage: patch_routed.py [board_path]
"""
import os, sys
import pcbnew

P = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    '~/workspace/projects/rp2040-IO-Expander/split/zero_board/zero_board.kicad_pcb')
b = pcbnew.LoadBoard(P)

for fp in b.GetFootprints():
    if fp.GetReference() == 'U1':
        for p in fp.Pads():
            p.SetSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.90), pcbnew.FromMM(0.60)))
        print('U1 pads shrunk to 0.90x0.60')

for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() != 'GND':
            continue
        pp = p.GetPosition()
        # J2 shell pads (all four S1) and J1's GND edge pad: their In1
        # thermal relief otherwise ends up with a single spoke
        # (which one starves depends on the route's zone fragments).
        if fp.GetReference() == 'J2' and p.GetNumber() == 'S1':
            p.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            print(f'J2 S1 ({pp.x/1e6:.2f},{pp.y/1e6:.2f}) -> solid zone connection')
        if fp.GetReference() == 'J1' and abs(pp.x / 1e6 - 1.68) < 0.05 \
                and abs(pp.y / 1e6 - 4.13) < 0.05:
            p.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            print('J1 GND edge pad -> solid zone connection')

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(P)
print('saved', P)
