#!/usr/bin/env python3
"""Move R1/R2 (CC pulldowns, B.Cu) out of FFC J4's courtyard/cable area and
rip the CC1/CC2 tracks so the router can redo them.
R1: (6.3,16.9) -> (4.2,17.6); R2: (11.7,16.9) -> (12.6,18.2)."""
import pcbnew, os

MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
moves = {"R1": (3.2, 12.2), "R2": (14.6, 12.2)}
for fp in b.GetFootprints():
    ref = fp.GetReference()
    if ref in moves:
        x, y = moves[ref]
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        print("moved", ref, "->", x, y)
# rip CC1/CC2 tracks
n = 0
for t in list(b.GetTracks()):
    if False:
        b.Remove(t)
        n += 1
print("ripped CC tracks:", n)
pcbnew.SaveBoard(PATH, b)
print("saved")
