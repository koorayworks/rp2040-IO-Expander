#!/usr/bin/env python3
"""Graft from a JSON element dump: delete the nets' copper from the
r16 base board and rebuild the donor's elements from JSON."""
import json, os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
MB = os.path.join(ROOT, 'split', 'module_board')
BASE = os.path.join(MB, 'backup', 'redo_v16_routed_prefinish.kicad_pcb')
JSONF = os.path.join(MB, 'backup', 'r17_gpio0_gpio4.json')
OUT = os.path.join(MB, 'module_board.kicad_pcb')
mm = pcbnew.FromMM
F, B = pcbnew.F_Cu, pcbnew.B_Cu

elems = json.load(open(JSONF))
want = {e['net'] for e in elems}

b = None
for _ in range(10):
    b = pcbnew.LoadBoard(BASE)
    if hasattr(b, 'GetFootprints'):
        break
NETS = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        try:
            n = pad.GetNet()
            if n and n.GetNetname():
                NETS.setdefault(n.GetNetname(), n)
        except Exception:
            pass

removed = 0
for t in list(b.GetTracks()):
    try:
        name = t.GetNet().GetNetname() if t.GetNet() else ''
    except Exception:
        continue
    if name in want:
        b.Remove(t)
        removed += 1
print('removed base elements:', removed)

added = 0
for e in elems:
    if e['kind'] == 'seg':
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(e['x1']), mm(e['y1'])))
        t.SetEnd(pcbnew.VECTOR2I(mm(e['x2']), mm(e['y2'])))
        t.SetWidth(mm(e['w']))
        t.SetLayer(e['layer'])
        t.SetNet(NETS[e['net']])
        b.Add(t)
    else:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(e['x']), mm(e['y'])))
        v.SetWidth(mm(e['w']))
        v.SetDrill(mm(e['d']))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(F, B)
        v.SetNet(NETS[e['net']])
        b.Add(v)
    added += 1
print('added donor elements:', added)
pcbnew.SaveBoard(OUT, b)
print('saved graft board')
