#!/usr/bin/env python3
"""Round-45: MINIMAL change on the r41 base (placement_v36,
5 pairs). Rounds 42-44 showed a dose-response: the more
seeds added per round, the more rotation damage (6, 8,
13 items; r44 even broke USB_D+ and 3V3_BAT). So r45
adds exactly ONE seed:

  - EX5: I1 extension (12.6,25.8)->(13.88,25.8).
    Closed EX5 in r42, and hand-adding the same segment
    to the r41 ROUTED board closed EX5 there too
    (redo_v41_handfinish_a: 4 pairs {GPIO6, GPIO10,
    GPIO27, GPIO28}, clearance 0).

Everything else is left exactly as r41.
"""
import os, pcbnew
ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC = os.path.join(ROOT, 'split', 'module_board', 'backup',
                   'placement_v36_round41seeds.kicad_pcb')
OUT = os.path.join(ROOT, 'split', 'module_board',
                   'module_board.kicad_pcb')
b = pcbnew.LoadBoard(SRC)
mm = pcbnew.FromMM
NETS = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname():
            NETS.setdefault(n.GetNetname(), n)
t = pcbnew.PCB_TRACK(b)
t.SetStart(pcbnew.VECTOR2I(mm(12.6), mm(25.8)))
t.SetEnd(pcbnew.VECTOR2I(mm(13.88), mm(25.8)))
t.SetWidth(mm(0.15)); t.SetLayer(pcbnew.In1_Cu); t.SetNet(NETS['EX5'])
b.Add(t)
pcbnew.SaveBoard(OUT, b)
print('saved')
