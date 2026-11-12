#!/usr/bin/env python3
"""Import module-board Freerouting SES, refill zones, save."""
import os, pcbnew

P = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander/split/module_board/module_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
ok = pcbnew.ImportSpecctraSES(b, '/tmp/module_board.ses')
print('SES import:', ok)
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print('tracks:', len(b.GetTracks()))
