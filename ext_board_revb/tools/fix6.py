#!/usr/bin/env python3
"""fix6: PR1 east loop on B, 3V3 east loop, 3V3_BAT I2 detour."""
import pcbnew, os
MM = pcbnew.FromMM; TM = pcbnew.ToMM
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups/board_micro9.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
LAY = {"F": pcbnew.F_Cu, "I2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}

def ep(t):
    a, c = t.GetStart(), t.GetEnd()
    return (TM(a.x), TM(a.y)), (TM(c.x), TM(c.y))

def close(p, q, tol=0.011): return abs(p[0]-q[0]) < tol and abs(p[1]-q[1]) < tol

def seg_is(t, net, p, q):
    if t.GetClass() == "PCB_VIA" or t.GetNetname() != net: return False
    a, c = ep(t)
    return (close(a, p) and close(c, q)) or (close(a, q) and close(c, p))

def via_is(t, net, p):
    if t.GetClass() != "PCB_VIA" or t.GetNetname() != net: return False
    pos = t.GetPosition()
    return close((TM(pos.x), TM(pos.y)), p)

SEG_DELS = [
    ("PR1", (4.52,29.46), (5.05,35.30)), ("PR1", (5.05,35.30), (4.55,35.95)),
    ("PR1", (5.05,35.30), (4.95,36.25)),
    ("3V3", (5.18,29.30), (4.95,29.75)), ("3V3", (4.95,29.75), (4.95,34.30)),
    ("3V3", (4.95,34.30), (4.95,34.50)),
    ("3V3_BAT", (4.75,33.70), (3.69,32.99)),
]
VIA_DELS = [("PR1", (4.52,29.46)), ("PR1", (5.05,35.30))]

to_delete = []
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        if any(via_is(t, n, p) for (n, p) in VIA_DELS): to_delete.append(t)
        continue
    if any(seg_is(t, n, p, q) for (n, p, q) in SEG_DELS): to_delete.append(t)
print("delete:", len(to_delete))
for t in to_delete: b.Remove(t)

def add_track(net, layer, p, q, w=0.10):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
    t.SetEnd(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])))
    t.SetWidth(MM(w)); t.SetLayer(LAY[layer]); t.SetNet(b.FindNet(net))
    b.Add(t)

# 3V3 v6: south at x5.02, around EX1 diag east end, west along y34.80 into web
for (p, q) in [((5.18,29.30),(5.02,29.80)), ((5.02,29.80),(5.02,33.20)), ((5.02,33.20),(5.75,33.60)),
               ((5.75,33.60),(5.75,34.80)), ((5.75,34.80),(4.95,34.80)), ((4.95,34.80),(4.95,34.55))]:
    add_track("3V3", "B", p, q)
# PR1 v9: north then east loop, land R5.1 from the east
for (p, q) in [((4.50,29.56),(4.50,29.05)), ((4.50,29.05),(5.60,29.05)), ((5.60,29.05),(5.70,32.80)),
               ((5.70,32.80),(6.30,33.30)), ((6.30,33.30),(6.30,34.30)), ((6.30,34.30),(5.60,35.30)),
               ((5.60,35.30),(5.45,35.45))]:
    add_track("PR1", "B", p, q)
# 3V3_BAT I2 detour
add_track("3V3_BAT", "I2", (4.75,33.70), (4.20,33.95))
add_track("3V3_BAT", "I2", (4.20,33.95), (3.69,32.99))
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX6 DONE")
