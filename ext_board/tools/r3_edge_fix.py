#!/usr/bin/env python3
"""Round-3 edge repair: Freerouting treated the JLEG castellation pads'
connection point as anchor+1.95mm along the pad axis, so GPIO2/3/4/7
spines run at x=18.25-18.67, OUTSIDE the 18.0mm outline. Delete those
and re-route the four nets through the west channel (x=15.45/15.70,
clear of the PTH pad copper whose west edge is x=15.87)."""
import pcbnew

SRC = "/tmp/r3_w4.kicad_pcb"
OUT = "/tmp/r3_w5.kicad_pcb"
b = pcbnew.LoadBoard(SRC)
codes = {}
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname():
            codes[p.GetNetname()] = p.GetNetCode()

def mm(v): return pcbnew.ToMM(v)

def seg_key(t):
    s, e = t.GetStart(), t.GetEnd()
    return (round(mm(s.x), 2), round(mm(s.y), 2), round(mm(e.x), 2), round(mm(e.y), 2))

EXPLICIT = {
    # net, (x1,y1,x2,y2) either orientation
    ("GPIO2", (16.67, 6.67, 18.62, 6.67)), ("GPIO2", (16.51, 10.38, 18.62, 10.38)),
    ("GPIO4", (16.67, 11.75, 18.62, 11.75)),
    ("GPIO7", (16.67, 19.37, 18.62, 19.37)), ("GPIO7", (18.25, 31.97, 13.97, 36.25)),
}
def match_explicit(net, key):
    x1, y1, x2, y2 = key
    return (net, (x1, y1, x2, y2)) in EXPLICIT or (net, (x2, y2, x1, y1)) in EXPLICIT

removed = {n: 0 for n in ("GPIO2", "GPIO3", "GPIO4", "GPIO7")}
for t in list(b.GetTracks()):
    net = t.GetNetname()
    if net not in removed:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        pp = t.GetPosition()
        if mm(pp.x) > 17.5:
            b.Remove(t); removed[net] += 1
        continue
    key = seg_key(t)
    if min(key[0], key[2]) > 17.5 or match_explicit(net, key):
        b.Remove(t); removed[net] += 1
print("removed:", removed, flush=True)

def trk(net, layer, x1, y1, x2, y2):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    t.SetWidth(pcbnew.FromMM(0.10)); t.SetLayer(layer); t.SetNetCode(codes[net])
    b.Add(t)

def via(net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    v.SetDrill(pcbnew.FromMM(0.20)); v.SetWidth(pcbnew.FromMM(0.40))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNetCode(codes[net])
    b.Add(v)

IN2 = pcbnew.In2_Cu; F = pcbnew.F_Cu
# GPIO2: pad2 west on In2, spine x=15.70 down to existing vertex (15.72,11.32)
trk("GPIO2", IN2, 16.67, 6.67, 15.70, 6.67)
trk("GPIO2", IN2, 15.70, 6.67, 15.72, 11.32)
# GPIO3: F stub west, via, In2 spine x=15.45, diagonal to existing (14.26,33.64)
trk("GPIO3", F, 16.67, 9.21, 15.45, 9.21)
via("GPIO3", 15.45, 9.21)
trk("GPIO3", IN2, 15.45, 9.21, 15.45, 32.45)
trk("GPIO3", IN2, 15.45, 32.45, 14.26, 33.64)
# GPIO4: In2 stub west, spine x=15.70, east along y=18.30 to kept segment end (17.58,18.30)
trk("GPIO4", IN2, 16.67, 11.75, 15.70, 11.75)
trk("GPIO4", IN2, 15.70, 11.75, 15.70, 18.30)
trk("GPIO4", IN2, 15.70, 18.30, 17.58, 18.30)
# GPIO7: F stub west, via, In2 spine x=15.70, diagonal to kept F vertex (13.97,36.25), via
trk("GPIO7", F, 16.67, 19.37, 15.70, 19.37)
via("GPIO7", 15.70, 19.37)
trk("GPIO7", IN2, 15.70, 19.37, 15.70, 34.28)
trk("GPIO7", IN2, 15.70, 34.28, 13.97, 36.25)
via("GPIO7", 13.97, 36.25)
print("added repair geometry", flush=True)

f = pcbnew.ZONE_FILLER(b); print("fill:", f.Fill(b.Zones()), flush=True)
pcbnew.SaveBoard(OUT, b)
print("saved:", OUT, flush=True)
