#!/usr/bin/env python3
"""fix15: rotate U4 to 0deg (vertical pin columns), delete copper that grazed
old U4 rects / dangling stubs, repair 3V3 winding mid-section."""
import pcbnew, os
MM = pcbnew.FromMM; TM = pcbnew.ToMM
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups/board_micro9.kicad_pcb")
b = pcbnew.LoadBoard(PATH)

for fp in b.GetFootprints():
    if fp.GetReference() == "U4":
        fp.SetOrientationDegrees(0.0)
        print("U4 rotated to 0; pads now:")
        for pad in fp.Pads():
            p = pad.GetPosition()
            print(f"  pad{pad.GetNumber()} [{pad.GetNetname()}] ({TM(p.x):.2f},{TM(p.y):.2f})")

def ep(t):
    a, c = t.GetStart(), t.GetEnd()
    return (TM(a.x), TM(a.y)), (TM(c.x), TM(c.y))
def close(p, q, tol=0.011): return abs(p[0]-q[0]) < tol and abs(p[1]-q[1]) < tol
def seg_is(t, net, p, q):
    if t.GetClass() == "PCB_VIA" or t.GetNetname() != net: return False
    a, c = ep(t)
    return (close(a, p) and close(c, q)) or (close(a, q) and close(c, p))

SEG_DELS = [
    # 3V3 north stub + dip + vertical (dangling after rotation)
    ("3V3", (3.50,29.75), (3.50,28.25)), ("3V3", (3.50,28.25), (4.55,28.25)),
    ("3V3", (4.55,28.25), (4.58,28.50)), ("3V3", (4.58,28.50), (4.95,28.90)),
    ("3V3", (4.95,28.90), (5.18,28.95)), ("3V3", (5.18,28.95), (5.18,33.62)),
    # 3V3 winding north graze segs (old U4.2 rect)
    ("3V3", (3.40,29.90), (3.45,29.85)), ("3V3", (3.45,29.85), (3.45,29.80)),
    ("3V3", (3.35,29.95), (3.40,29.90)),
    # 3V3 winding mid (violating section vs old U4.8 rect corner)
    ("3V3", (3.15,30.50), (3.20,30.55)), ("3V3", (3.20,30.55), (3.20,30.60)),
    ("3V3", (3.20,30.60), (3.25,30.60)), ("3V3", (3.25,30.60), (3.25,30.65)),
    ("3V3", (3.25,30.65), (3.35,30.75)), ("3V3", (3.35,30.75), (3.35,31.10)),
    ("3V3", (3.31,31.20), (3.52,31.20)),
    # 3V3_BAT chain north graze segs (old U4.6 rect)
    ("3V3_BAT", (3.95,31.30), (3.95,31.35)), ("3V3_BAT", (3.90,31.40), (3.95,31.35)),
    ("3V3_BAT", (3.90,31.55), (3.90,31.40)), ("3V3_BAT", (3.85,31.60), (3.90,31.55)),
]
to_delete = [t for t in list(b.GetTracks()) if any(seg_is(t, n, p, q) for (n, p, q) in SEG_DELS)]
print("delete:", len(to_delete), "of", len(SEG_DELS))
for t in to_delete: b.Remove(t)

def add_track(net, layer, p, q, w=0.10):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
    t.SetEnd(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])))
    t.SetWidth(MM(w)); t.SetLayer({"F": pcbnew.F_Cu, "I2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}[layer])
    t.SetNet(b.FindNet(net))
    b.Add(t)

# winding repair: (3.15,30.50) west/south swing to via chain (3.31,31.75)
for (p, q) in [((3.15,30.50),(3.00,30.52)), ((3.00,30.52),(3.00,31.30)),
               ((3.00,31.30),(3.02,31.55)), ((3.02,31.55),(3.31,31.75)),
               ((3.35,30.00),(3.10,30.03))]:  # land on U4 pad2 (VOUT) rect west edge
    add_track("3V3", "B", p, q)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX15 DONE")
