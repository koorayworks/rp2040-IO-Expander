#!/usr/bin/env python3
"""Round-43: seeds for r42's open nets on the r42 base
(placement_v37). r42: 6 pairs {GPIO1, GPIO5, GPIO6,
GPIO10, GPIO14, GPIO28}; EX5 and GPIO27 closed.

  - GPIO5: I1 stub from its existing J-side via
    (9.0,19.2) north to (9.0,17.9). Checker pass 0.30.
  - GPIO6: extend the r42 I1 anchor (10.1,18.2) north
    to (10.25,17.6). The straighter (9.9,16.9) fails
    vs GPIO4's I1 track end (9.8,17.3) at 0.0096.
  - GPIO10: I2 south stub from the r42 seed via
    (14.35,15.7) to (14.35,19.0) + via40 there.
    Checker pass 0.66 / via 0.51.
  - GPIO14: J2 B stub (11.1,22.075)->(11.1,22.55),
    the r34/r38 proven seed. Checker pass 0.137.
  - GPIO28: extend the r42 J1 F stub east along the
    inter-row corridor (5.55,21.5)->(6.2,21.5).
    Checker pass 0.137 (tight vs GPIO0 via (6.3,21.1)).
    North fails vs GPIO27's F track; a tip via fails
    vs USB_D+'s I2 track through (5.55,22.2).
  - GPIO1: NO new seed. Its J2 B stub area is walled
    (S: GPIO2 via (7.35,20.6), W: J2.24 GND pad,
    tip via: J1.10 pad). It closed unseeded-extra in
    r37/r41; leave it to rotation.
All candidates verified with checker.py against the
v37 placement (pass >= 0.099).
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC = os.path.join(ROOT, 'split', 'module_board', 'backup',
                   'placement_v37_round42seeds.kicad_pcb')
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

stub(9.0, 19.2, 9.0, 17.9, I1, 'GPIO5')
stub(10.1, 18.2, 10.25, 17.6, I1, 'GPIO6')
stub(14.35, 15.7, 14.35, 19.0, I2, 'GPIO10')
via40(14.35, 19.0, 'GPIO10')
stub(11.1, 22.075, 11.1, 22.55, B, 'GPIO14')
stub(5.55, 21.5, 6.2, 21.5, F, 'GPIO28')

pcbnew.SaveBoard(OUT, b)
print('saved')
