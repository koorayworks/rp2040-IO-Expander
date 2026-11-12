#!/usr/bin/env python3
"""Dump tracks/vias of given nets (argv: board, net...) to JSON on stdout.
One board load per process (pcbnew gets flaky on repeated loads)."""
import json, sys, pcbnew

path = sys.argv[1]
want = set(sys.argv[2:])
b = None
for _ in range(10):
    b = pcbnew.LoadBoard(path)
    if hasattr(b, 'GetFootprints'):
        break
out = []
for t in b.GetTracks():
    try:
        name = t.GetNet().GetNetname() if t.GetNet() else ''
    except Exception:
        continue
    if name not in want:
        continue
    if t.Type() == pcbnew.PCB_TRACE_T:
        out.append({'kind': 'seg', 'net': name, 'layer': t.GetLayer(),
                    'x1': pcbnew.ToMM(t.GetStartX()), 'y1': pcbnew.ToMM(t.GetStartY()),
                    'x2': pcbnew.ToMM(t.GetEndX()), 'y2': pcbnew.ToMM(t.GetEndY()),
                    'w': pcbnew.ToMM(t.GetWidth())})
    elif t.Type() == pcbnew.PCB_VIA_T:
        out.append({'kind': 'via', 'net': name,
                    'x': pcbnew.ToMM(t.GetPosition().x), 'y': pcbnew.ToMM(t.GetPosition().y),
                    'w': pcbnew.ToMM(t.GetWidth()), 'd': pcbnew.ToMM(t.GetDrill())})
print(json.dumps(out))
