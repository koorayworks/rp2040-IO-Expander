#!/usr/bin/env python3
"""Delete all tracks/vias of the given nets from module_board.kicad_pcb
(back it up first), so a freerouting pass re-routes only those nets
in the frozen field of everything else."""
import os, shutil, sys, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
P = os.path.join(ROOT, 'split', 'module_board', 'module_board.kicad_pcb')
SRC = os.path.join(ROOT, 'split', 'module_board', 'backup',
                   'redo_v17_routed_prefinish.kicad_pcb')
TARGETS = {'GPIO1', 'GPIO3', 'GPIO6', 'USB_D-', 'GPIO29'}

b = pcbnew.LoadBoard(SRC)
codes = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        try:
            n = pad.GetNet()
            if n and n.GetNetname():
                codes[n.GetNetname()] = pad.GetNetCode()
        except Exception:
            pass
removed = 0
for t in list(b.GetTracks()):
    try:
        if t.GetNetCode() in {codes[n] for n in TARGETS if n in codes}:
            b.Remove(t)
            removed += 1
    except Exception:
        continue
print('removed', removed, 'tracks/vias of', sorted(TARGETS))
pcbnew.SaveBoard(P, b)
print('saved stripped board to module_board.kicad_pcb')
