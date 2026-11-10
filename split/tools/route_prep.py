#!/usr/bin/env python3
"""Fill the GND plane zone and export Specctra DSN for Freerouting."""
import os, sys, pcbnew

P = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander/split/zero_board/zero_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(P, b)
ok = pcbnew.ExportSpecctraDSN(b, '/tmp/zero_board.dsn')
print('DSN export:', ok)
