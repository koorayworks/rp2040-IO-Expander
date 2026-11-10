#!/usr/bin/env python3
"""Import Freerouting SES, refill zones, save."""
import os, pcbnew

P = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander/split/zero_board/zero_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
ok = pcbnew.ImportSpecctraSES(b, '/tmp/zero_board.ses')
print('SES import:', ok)
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print('tracks:', len(b.GetTracks()))
