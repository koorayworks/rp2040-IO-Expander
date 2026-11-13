#!/usr/bin/env python3
"""Round-44: seeds for r43's open nets on the r43 base
(placement_v38). r43: 8 items / 6 nets {GPIO6 x2, GPIO7,
GPIO8 x2, GPIO11, GPIO12, GPIO14}. Closed by r43 seeds:
GPIO1, GPIO5, GPIO10, GPIO28.

IMPORTANT correction: r41's GPIO7 'seed' via at
(9.9,14.6) never existed as GPIO7 -- a GPIO2 via sits
exactly there, so the via and its I2 stub flipped to
GPIO2 in the saved board (verified by dump on v36/v38).
GPIO7's closures in r41/r42 were rotation, not the seed.

  - GPIO6: F bridge from its J2 via (8.7,22.9) to
    (9.3,22.3), whose end touches its own J1.17 pad --
    bridges the J1/J2 chains directly. Plus I1 anchor
    extension (10.25,17.6)->(10.05,17.0) toward U1
    (checker 0.182 vs GPIO4's I1 track end).
  - GPIO8: J2 B stub (9.3,22.075)->(9.3,22.55) (r34
    proven) + J1 F stub (8.7,22.075)->(8.45,22.5)
    SW. NOTE: the SE variant (8.95,22.5) from r38
    CROSSES the new GPIO6 F bridge (the two seeds were
    checker-verified separately, not against each
    other -- first r44 attempt had shorting GPIO6/
    GPIO8 and was killed before routing). SW variant
    verified against the board WITH the bridge in it.
  - GPIO11: J2 B base stub (10.2,19.925)->(10.2,19.45)
    + U1 west escape F (12.75,15.164)->(12.3,15.7) +
    via40 (12.3,15.7). SE escape fails vs USB_D+ pad.
  - GPIO12: U1 east escape F (13.65,13.963)->
    (14.127,13.963)->(14.127,14.6). Its J stubs were
    already present (dangling, no vias possible:
    J2-end via fails vs GPIO4 via at 0.474mm centres).
  - GPIO7: NO seed. U1.26 escape fails E/W/S in the
    checker (0.025 vs U1.24/U1.27 pads, GPIO1 F track
    to the south). Leave to rotation.
  - GPIO14: NO new seed. B stub extension E fails vs
    GPIO26's B track, W fails vs GPIO12's B stub, tip
    via fails vs J1.23 pad. Leave to rotation.
All candidates verified with checker.py against the
v38 placement (pass >= 0.099).
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC = os.path.join(ROOT, 'split', 'module_board', 'backup',
                   'placement_v38_round43seeds.kicad_pcb')
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

stub(8.7, 22.9, 9.3, 22.3, F, 'GPIO6')
stub(10.25, 17.6, 10.05, 17.0, I1, 'GPIO6')
stub(9.3, 22.075, 9.3, 22.55, B, 'GPIO8')
stub(8.7, 22.075, 8.45, 22.5, F, 'GPIO8')
stub(10.2, 19.925, 10.2, 19.45, B, 'GPIO11')
stub(12.75, 15.164, 12.3, 15.7, F, 'GPIO11')
via40(12.3, 15.7, 'GPIO11')
stub(13.65, 13.963, 14.127, 13.963, F, 'GPIO12')
stub(14.127, 13.963, 14.127, 14.6, F, 'GPIO12')

pcbnew.SaveBoard(OUT, b)
print('saved')
