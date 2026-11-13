#!/usr/bin/env python3
"""Round-42: graft seeds for the 5 nets left open by r41
{EX5, GPIO6, GPIO10, GPIO27, GPIO28} onto the r41 base
(placement_v36 = r25 base + GPIO15 + USB_D+ + EX5/GPIO7/
GPIO26/GPIO6-jog grafts). r41 result: 5 pairs, GPIO7 and
GPIO26 closed.

  - EX5: extend the I1 stub east to the FFC-side via
    (13.88,25.74). r41's U1 chain reached the stub end
    (12.6,25.8) but stopped 1.28mm short of that via.
    Checker: clearance 1.59 vs placement.
  - GPIO6: I1 mid anchor from the existing J-side via
    (9.28,20.6) east/north (10.1,19.9)->(10.1,18.2).
    Direct F/I2 bridges are blocked (GPIO5 vias at
    (9.6,19.0)/(9.0,19.2), GPIO1 F track y~18, 3V3 I2
    track y=17.9, GPIO2/GPIO3 vias west). Checker pass.
  - GPIO10: proven U1 escape (r25/r30/r33 router shape):
    F (13.65,14.764)->(14.5,15.2)->(14.35,15.7) + via40.
    The v36 placement has NO stub on U1.37 at all.
  - GPIO27: B base stub on J2.6 (12.0,19.925)->(12.0,19.45),
    same pattern as GPIO9/GPIO13. Stub only (a tip via
    fails vs J1.26 USB_D+ pad). r41 left J2.6 pad alone.
  - GPIO28: F base stub on J1.5 (5.7,22.075)->(5.55,21.5)
    north into the inter-row corridor. South is blocked
    by GPIO26's via (5.7,22.75). Stub only. r41 left
    J1.5 pad alone.
All candidates verified with checker.py against the
v36 placement (pass >= 0.099).
"""
import os, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC = os.path.join(ROOT, 'split', 'module_board', 'backup',
                   'placement_v36_round41seeds.kicad_pcb')
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

stub(12.6, 25.8, 13.88, 25.8, I1, 'EX5')
stub(9.28, 20.6, 10.1, 19.9, I1, 'GPIO6')
stub(10.1, 19.9, 10.1, 18.2, I1, 'GPIO6')
stub(13.65, 14.764, 14.5, 15.2, F, 'GPIO10')
stub(14.5, 15.2, 14.35, 15.7, F, 'GPIO10')
via40(14.35, 15.7, 'GPIO10')
stub(12.0, 19.925, 12.0, 19.45, B, 'GPIO27')
stub(5.7, 22.075, 5.55, 21.5, F, 'GPIO28')

pcbnew.SaveBoard(OUT, b)
print('saved')
