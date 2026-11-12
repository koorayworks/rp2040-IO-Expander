#!/usr/bin/env python3
"""Dump all copper geometry of given nets: pads, track endpoints, vias.
Usage: python3 dump_net.py NET [NET ...]"""
import os, sys, pcbnew

P = os.environ.get('BOARD_PATH', os.path.expanduser(
    '~/workspace/projects/rp2040-IO-Expander/split/module_board/module_board.kicad_pcb'))
b = pcbnew.LoadBoard(P)
LAY = {0: 'F', 1: 'I1', 2: 'I2', 31: 'B'}
want = set(a for a in sys.argv[1:] if not a.endswith('.kicad_pcb'))

for fp in b.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname() in want:
            pos = pad.GetPosition()
            print(f"PAD {n.GetNetname()} {fp.GetReference()}.{pad.GetNumber()} "
                  f"({pcbnew.ToMM(pos.x):.3f},{pcbnew.ToMM(pos.y):.3f}) "
                  f"L{LAY.get(pad.GetLayer(), pad.GetLayer())} drill={pcbnew.ToMM(pad.GetDrillSize().x):.2f}")

for t in b.GetTracks():
    n = t.GetNet()
    if not n or n.GetNetname() not in want:
        continue
    nm = n.GetNetname()
    if t.Type() == pcbnew.PCB_VIA_T:
        pos = t.GetPosition()
        print(f"VIA {nm} ({pcbnew.ToMM(pos.x):.3f},{pcbnew.ToMM(pos.y):.3f})")
    else:
        s, e = t.GetStart(), t.GetEnd()
        print(f"SEG {nm} L{LAY.get(t.GetLayer(), t.GetLayer())} "
              f"({pcbnew.ToMM(s.x):.3f},{pcbnew.ToMM(s.y):.3f})->({pcbnew.ToMM(e.x):.3f},{pcbnew.ToMM(e.y):.3f})")
