#!/usr/bin/env python3
"""Post-route patch for the module board.

- J6 (JST PH) pin 2 is a GND PTH pad: give it a solid zone connection
  so the In1 GND pour cannot starve its thermal spokes (same fix as
  the Zero board's J1/J2 GND PTH pads).
"""
import os, pcbnew

P = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander/split/module_board/module_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
for fp in b.GetFootprints():
    if fp.GetReference() == 'J6':
        for pad in fp.Pads():
            if str(pad.GetNumber()) == '2':
                pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
                print('J6 pin2 GND -> solid zone connection')
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print('saved', P)
