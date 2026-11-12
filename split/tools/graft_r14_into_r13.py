#!/usr/bin/env python3
"""Graft experiment: take round-13's board (best: 5 pairs) and
replace the copper of GPIO3 + USB_D+ with round-14's versions
(both fully connected in r14, broken in r13). Validated by DRC
afterwards; abandoned if clearance explodes."""
import os, pcbnew
ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
R13 = os.path.join(ROOT, 'split', 'module_board', 'backup', 'redo_v13_routed_prefinish.kicad_pcb')
R14 = os.path.join(ROOT, 'split', 'module_board', 'backup', 'redo_v14_routed_prefinish.kicad_pcb')
OUT = os.path.join(ROOT, 'split', 'module_board', 'module_board.kicad_pcb')
TARGETS = {'GPIO3', 'USB_D+'}

b13 = pcbnew.LoadBoard(R13)
b14 = pcbnew.LoadBoard(R14)

# delete r13 copper for target nets
kill = []
for t in b13.GetTracks():
    if t.GetNet() and t.GetNet().GetNetname() in TARGETS:
        kill.append(t)
for t in kill:
    b13.Remove(t)
print('removed r13 elements:', len(kill))

NETS = {}
for fp in b13.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname():
            NETS.setdefault(n.GetNetname(), n)

added = 0
for t in b14.GetTracks():
    if not (t.GetNet() and t.GetNet().GetNetname() in TARGETS):
        continue
    d = t.Duplicate()
    d.SetNet(NETS[t.GetNet().GetNetname()])
    b13.Add(d)
    added += 1
print('grafted r14 elements:', added)
pcbnew.SaveBoard(OUT, b13)
print('saved graft board')
