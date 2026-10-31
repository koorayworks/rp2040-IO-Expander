#!/usr/bin/env python3
"""Post-fixes for the run-C (strip keepout) board w6:
1) widen 0.075mm fanout tracks to 0.10mm;
2) USB_D-_C: J2.A7 via at (9.28,1.22) -- centre inside A7's pad,
   >=0.12mm clear of A6/B6 pads and of the D+ escape (y=1.60 line,
   via top edge 1.42 vs track edge 1.55) -- plus an In2 hop west to
   the B7 escape's In2 run at (8.41,1.77);
3) drop two dangling vias Freerouting left (RESET, TB5) -- verified
   by DRC afterwards that both nets stay connected."""
import pcbnew, os

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board")
W = os.path.join(BASE, "tools", "r3_work")
SRC = os.path.join(W, "w6.kicad_pcb")
OUT = os.path.join(W, "w7.kicad_pcb")
b = pcbnew.LoadBoard(SRC)
code = None
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() == "USB_D-_C":
            code = p.GetNetCode()
print("USB_D-_C net code:", code, flush=True)

n = 0
for t in b.GetTracks():
    if t.Type() != pcbnew.PCB_VIA_T and pcbnew.ToMM(t.GetWidth()) < 0.099:
        t.SetWidth(pcbnew.FromMM(0.10)); n += 1
print("widened:", n, flush=True)

dropped = 0
for t in list(b.GetTracks()):
    if t.Type() != pcbnew.PCB_VIA_T:
        continue
    p = t.GetPosition()
    x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    if (t.GetNetname() == "RESET" and abs(x - 6.5756) < 0.01 and abs(y - 29.7568) < 0.01) or \
       (t.GetNetname() == "TB5" and abs(x - 7.7989) < 0.01 and abs(y - 32.8374) < 0.01):
        b.Remove(t); dropped += 1
print("dangling vias dropped:", dropped, flush=True)

via = pcbnew.PCB_VIA(b)
via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(9.28), pcbnew.FromMM(1.22)))
via.SetDrill(pcbnew.FromMM(0.20)); via.SetWidth(pcbnew.FromMM(0.40))
via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNetCode(code)
b.Add(via)
def trk(x1, y1, x2, y2):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    t.SetWidth(pcbnew.FromMM(0.10)); t.SetLayer(pcbnew.In2_Cu); t.SetNetCode(code)
    b.Add(t)
trk(9.28, 1.22, 8.41, 1.22)
trk(8.41, 1.22, 8.41, 1.77)
print("USB_D-_C join added", flush=True)

f = pcbnew.ZONE_FILLER(b); print("fill:", f.Fill(b.Zones()), flush=True)
pcbnew.SaveBoard(OUT, b)
print("saved:", OUT, flush=True)
