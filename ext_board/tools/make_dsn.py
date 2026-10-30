#!/usr/bin/env python3
"""Export Specctra DSN from the working board, with rule-area (keepout)
zones removed in the export copy only (DSN export segfaults with them).
Existing tracks are exported as wires (Freerouting treats them as fixed)."""
import pcbnew, os, sys

SRC = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/endgame.dsn"
TMPB = "/tmp/endgame_nok.kicad_pcb"

b = pcbnew.LoadBoard(SRC)
for z in list(b.Zones()):
    if z.GetIsRuleArea():
        b.Remove(z)
pcbnew.SaveBoard(TMPB, b)
ok = pcbnew.ExportSpecctraDSN(b, OUT)
print("DSN export:", ok, "->", OUT)
