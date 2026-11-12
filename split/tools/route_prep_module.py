#!/usr/bin/env python3
"""Export module-board Specctra DSN WITHOUT the GND zone (Freerouting
routes GND as an ordinary net; see route_prep_noplane.py). The antenna
rule-area zone is KEPT -- it must reach the DSN as a keepout. The board
file itself is NOT saved, so both zones survive for the import step."""
import os, pcbnew
P = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander/split/module_board/module_board.kicad_pcb')
b = pcbnew.LoadBoard(P)
removed = 0
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Remove(z)
        removed += 1
print('copper zones removed for export:', removed, '| zones left:', len(list(b.Zones())))
ok = pcbnew.ExportSpecctraDSN(b, '/tmp/module_board.dsn')
print('DSN export:', ok)
