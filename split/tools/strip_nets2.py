#!/usr/bin/env python3
"""Like strip_nets.py but KEEPS the placement stubs/vias (from the
placement board) of the target nets -- only the router's own
copper is removed, so the re-route starts from the seeded pads."""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
MB = os.path.join(ROOT, 'split', 'module_board')
P = os.path.join(MB, 'module_board.kicad_pcb')
SRC = os.path.join(MB, 'backup', 'redo_v17_routed_prefinish.kicad_pcb')
PLC = os.path.join(MB, 'backup', 'placement_v14_round17seeds.kicad_pcb')
TARGETS = {'GPIO1', 'GPIO3', 'GPIO6', 'USB_D-', 'GPIO29'}

def netmap(b):
    m = {}
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            try:
                n = pad.GetNet()
                if n and n.GetNetname():
                    m[pad.GetNetCode()] = n.GetNetname()
            except Exception:
                pass
    return m

def key_seg(t, nm):
    return (nm.get(t.GetNetCode()), t.GetLayer(),
            round(pcbnew.ToMM(t.GetStartX()), 3), round(pcbnew.ToMM(t.GetStartY()), 3),
            round(pcbnew.ToMM(t.GetEndX()), 3), round(pcbnew.ToMM(t.GetEndY()), 3))

def key_via(t, nm):
    return (nm.get(t.GetNetCode()), 'VIA',
            round(pcbnew.ToMM(t.GetPosition().x), 3),
            round(pcbnew.ToMM(t.GetPosition().y), 3))

pb = pcbnew.LoadBoard(PLC)
pnm = netmap(pb)
keep = set()
for t in pb.GetTracks():
    nm = pnm.get(t.GetNetCode())
    if nm not in TARGETS:
        continue
    if t.Type() == pcbnew.PCB_TRACE_T:
        keep.add(key_seg(t, pnm))
        # stubs may be stored either direction
        k = key_seg(t, pnm)
        keep.add((k[0], k[1], k[4], k[5], k[2], k[3]))
    elif t.Type() == pcbnew.PCB_VIA_T:
        keep.add(key_via(t, pnm))
print('placement elements to keep:', len(keep))

b = pcbnew.LoadBoard(SRC)
nm = netmap(b)
removed = kept = 0
for t in list(b.GetTracks()):
    name = nm.get(t.GetNetCode())
    if name not in TARGETS:
        continue
    if t.Type() == pcbnew.PCB_TRACE_T:
        k = key_seg(t, nm)
    elif t.Type() == pcbnew.PCB_VIA_T:
        k = key_via(t, nm)
    else:
        continue
    if k in keep:
        kept += 1
    else:
        b.Remove(t)
        removed += 1
print(f'removed {removed} router elements, kept {kept} placement elements')
pcbnew.SaveBoard(P, b)
print('saved')
