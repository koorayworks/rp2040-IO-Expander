#!/usr/bin/env python3
"""Export Specctra DSN WITHOUT the GND zone: Freerouting then routes
GND as an ordinary net (tracks+vias), so KiCad-side zone fragmentation
cannot strand GND islands. The board file itself is NOT saved, so the
zone survives for route_import's refill."""
import os, pcbnew
P = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander/split/zero_board/zero_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
for z in list(b.Zones()):
    b.Remove(z)
print('zones removed for export:', len(list(b.Zones())) == 0)
ok = pcbnew.ExportSpecctraDSN(b, '/tmp/zero_board.dsn')
print('DSN export:', ok)
