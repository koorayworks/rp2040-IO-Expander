#!/usr/bin/env python3
"""Deterministic post-fixes on the run-2 merged board (checkpoint
board_step_r3_m2.kicad_pcb) reconstructing the verified 'w4' state:
1) widen Freerouting's 0.075mm fanout tracks to the 0.10mm minimum;
2) move the GP24 via (14.1795,30.651) -> (14.10,30.72): at 0.10 width
   the GP19 B.Cu stub came within 0.08mm of it, and the first nudge
   (14.10,30.65) broke hole/copper clearance to U1 pad 14 (BOOT);
3) USB_D-_C: Freerouting left J2.A7 unrouted. Add via at (9.28,1.38)
   (centre sits on A7's pad top edge, clear of A6/B6 pads and of the
   D+ escape at y=1.76) + In2 hop west to the B7 escape's In2 run."""
import pcbnew, os

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board")
SRC = os.path.join(BASE, "tools", "board_step_r3_m2.kicad_pcb")
OUT = os.path.join(BASE, "tools", "r3_work", "w4.kicad_pcb")
b = pcbnew.LoadBoard(SRC)

n = 0
for t in b.GetTracks():
    if t.Type() != pcbnew.PCB_VIA_T and pcbnew.ToMM(t.GetWidth()) < 0.099:
        t.SetWidth(pcbnew.FromMM(0.10)); n += 1
print("widened:", n, flush=True)

moved = 0
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GP24":
        p = t.GetPosition()
        if abs(pcbnew.ToMM(p.x) - 14.1795) < 0.01 and abs(pcbnew.ToMM(p.y) - 30.651) < 0.01:
            t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(14.10), pcbnew.FromMM(30.72)))
            moved += 1
print("GP24 via moved:", moved, flush=True)

code = None
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() == "USB_D-_C":
            code = p.GetNetCode()
via = pcbnew.PCB_VIA(b)
via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(9.28), pcbnew.FromMM(1.38)))
via.SetDrill(pcbnew.FromMM(0.20)); via.SetWidth(pcbnew.FromMM(0.40))
via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNetCode(code)
b.Add(via)
def trk(x1, y1, x2, y2):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    t.SetWidth(pcbnew.FromMM(0.10)); t.SetLayer(pcbnew.In2_Cu); t.SetNetCode(code)
    b.Add(t)
trk(9.28, 1.38, 8.51, 1.38)
trk(8.51, 1.38, 8.51, 1.76)
print("USB_D-_C join added", flush=True)

f = pcbnew.ZONE_FILLER(b); print("fill:", f.Fill(b.Zones()), flush=True)
pcbnew.SaveBoard(OUT, b)
print("saved:", OUT, flush=True)
