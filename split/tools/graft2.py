#!/usr/bin/env python3
"""Graft donor copper of given nets into a base board.
base  = redo_v16_routed_prefinish (3 pairs)
donor = redo_v17_routed_prefinish (GPIO0/GPIO4 completed by seeds)
All base tracks/vias of the nets are deleted, donor's are copied.
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
MB = os.path.join(ROOT, 'split', 'module_board')
BASE = os.path.join(MB, 'backup', 'redo_v16_routed_prefinish.kicad_pcb')
DONOR = os.path.join(MB, 'backup', 'redo_v17_routed_prefinish.kicad_pcb')
OUT = os.path.join(MB, 'module_board.kicad_pcb')
NETS_WANT = {'GPIO0', 'GPIO4'}

def load(path):
    for _ in range(8):
        b = pcbnew.LoadBoard(path)
        if hasattr(b, 'GetFootprints'):
            return b
    raise RuntimeError('bad load ' + path)

def netmap(b):
    m = {}
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            try:
                n = pad.GetNet()
                if n and n.GetNetname():
                    m[n.GetNetname()] = n
            except Exception:
                pass
    return m

b = load(BASE)
donor = load(DONOR)
NETS = netmap(b)

def tracks_of(board, path):
    for _ in range(8):
        try:
            return list(board.GetTracks())
        except Exception:
            board = load(path)
    raise RuntimeError('GetTracks kept failing for ' + path)

removed = 0
for t in list(b.GetTracks()):
    try:
        name = t.GetNet().GetNetname() if t.GetNet() else ''
    except Exception:
        continue
    if name in NETS_WANT:
        b.Remove(t)
        removed += 1
print('removed base elements:', removed)

added = 0
for t in tracks_of(donor, DONOR):
    try:
        name = t.GetNet().GetNetname() if t.GetNet() else ''
    except Exception:
        continue
    if name not in NETS_WANT:
        continue
    d = t.Duplicate()
    d.SetNet(NETS[name])
    b.Add(d)
    added += 1
print('added donor elements:', added)
pcbnew.SaveBoard(OUT, b)
print('saved graft board')
