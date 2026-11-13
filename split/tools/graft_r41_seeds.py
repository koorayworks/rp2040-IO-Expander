#!/usr/bin/env python3
"""Round-41: graft the next tier of proven seeds onto the
r40 base (placement_v35 = r25 base + GPIO15 + USB_D+):
  - EX5: I1 stub from its JP4 tap via (r38, EX5 closed)
  - GPIO7: anchor via (10.15,13.75) + I2 anchor + branch
    (r30/r37; v20 still has the floating r24-era stub)
  - GPIO26: J2 B stub (r39, GPIO26 closed)
  - GPIO6: J2 B stub + tip via + jog (current placement)
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC = os.path.join(ROOT, 'split', 'module_board', 'backup',
                   'placement_v35_round40seeds.kicad_pcb')
OUT = os.path.join(ROOT, 'split', 'module_board',
                   'module_board.kicad_pcb')
b = pcbnew.LoadBoard(SRC)
mm = pcbnew.FromMM
F, B, I1, I2 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu

NETS = {}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n = pad.GetNet()
        if n and n.GetNetname():
            NETS.setdefault(n.GetNetname(), n)

def stub(x1, y1, x2, y2, layer, net):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(0.15)); t.SetLayer(layer); t.SetNet(NETS[net])
    b.Add(t)

def via40(x, y, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(0.40)); v.SetDrill(mm(0.20))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F, B); v.SetNet(NETS[net])
    b.Add(v)

stub(10.9, 25.79, 12.6, 25.8, I1, 'EX5')
# GPIO7: (10.15,13.75) is taken on THIS base by GPIO6's
# via (10.04,13.823) -- the graft flipped to GPIO6.
# Use a fresh dive via at (9.9,14.6) instead.
via40(9.9, 14.6, 'GPIO7')
stub(9.9, 14.6, 10.6, 15.0, I2, 'GPIO7')
# (the S stub (9.9,14.6)->(9.9,16.3) touched GPIO2's
# I2 web on this base and flipped -- dropped)
stub(11.7, 22.075, 11.7, 22.4, B, 'GPIO26')
# GPIO6: J2 stub + tip via already exist on this base;
# only the r37 jog is new.
stub(8.7, 22.9, 8.9, 22.65, B, 'GPIO6')

pcbnew.SaveBoard(OUT, b)
print('saved')
