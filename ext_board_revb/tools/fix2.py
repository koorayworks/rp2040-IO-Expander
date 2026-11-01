#!/usr/bin/env python3
"""fix2 v2: single-scan collect, then remove/patch/add (pcbnew Remove breaks
iteration, so never call GetTracks after a Remove)."""
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

PATCHMAP = {
    "VBAT": {(11.60,31.20):(11.62,31.20), (11.60,31.25):(11.62,31.25),
             (10.55,33.80):(10.58,33.82), (10.50,33.85):(10.56,33.88), (10.50,33.90):(10.56,33.94)},
    "BOOST_SW": {(11.60,31.85):(11.62,31.85), (11.60,31.90):(11.62,31.90)},
    "3V3_BAT": {(9.70,33.90):(9.72,33.90), (9.70,33.85):(9.72,33.85), (9.70,33.05):(9.72,33.05), (9.70,33.00):(9.72,33.00)},
}
SEG_DELS = [
    ("3V3", (6.64,19.81), (6.56,19.74)),
    ("3V3_BAT", (3.50,32.45), (3.55,32.40)), ("3V3_BAT", (4.75,33.70), (3.50,32.45)),
    ("3V3_BAT", (7.00,36.05), (8.00,36.05)), ("3V3_BAT", (6.85,35.90), (7.00,36.05)),
    ("PR1", (3.85,36.25), (4.95,36.25)), ("PR1", (4.10,36.00), (3.85,36.25)),
    ("VBAT", (11.90,31.55), (12.05,31.70)), ("VBAT", (12.05,31.70), (12.45,31.30)),
]
VIA_DELS = [("3V3_BAT", (3.50,32.45)), ("3V3_BAT", (7.00,36.05)), ("PR1", (3.85,36.25)), ("VBAT", (12.05,31.70))]

to_delete, patches = [], []
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        if any(via_is(t, n, p) for (n, p) in VIA_DELS): to_delete.append(t)
        continue
    if any(seg_is(t, n, p, q) for (n, p, q) in SEG_DELS): to_delete.append(t); continue
    net = t.GetNetname()
    if net == "3V3" and t.GetLayer() == pcbnew.B_Cu:
        a, c = ep(t)
        if all(2.95 <= x <= 3.60 and 29.90 <= y <= 31.95 for (x, y) in (a, c)):
            to_delete.append(t); continue
        mx, my = (a[0]+c[0])/2, (a[1]+c[1])/2
        if 4.42 <= mx <= 4.68 and 34.97 <= my <= 35.18:
            to_delete.append(t); continue
    mp = PATCHMAP.get(net)
    if mp:
        a, c = ep(t)
        na = mp.get((round(a[0],2), round(a[1],2)))
        nc = mp.get((round(c[0],2), round(c[1],2)))
        if na or nc:
            patches.append((t, na or a, nc or c))
print("delete:", len(to_delete), "patch:", len(patches))
for t in to_delete: b.Remove(t)
for (t, na, nc) in patches:
    t.SetStart(pcbnew.VECTOR2I(MM(na[0]), MM(na[1])))
    t.SetEnd(pcbnew.VECTOR2I(MM(nc[0]), MM(nc[1])))

def add_track(net, layer, p, q, w=0.10):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
    t.SetEnd(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])))
    t.SetWidth(MM(w)); t.SetLayer(LAY[layer]); t.SetNet(b.FindNet(net))
    b.Add(t)

def add_via(net, p):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(MM(0.20)); v.SetWidth(MM(0.40)); v.SetNet(b.FindNet(net))
    b.Add(v)

# 3V3 U4 links
for (p, q) in [((3.31,31.85),(3.10,31.85)), ((3.31,31.05),(3.31,31.85)), ((3.31,31.20),(3.52,31.20)),
               ((3.31,31.05),(3.90,30.80)), ((3.90,30.80),(3.90,30.05)), ((3.90,30.05),(3.31,29.90)),
               ((3.31,29.90),(3.50,29.75)), ((3.50,29.75),(3.50,28.25)), ((3.50,28.25),(5.30,28.25)),
               ((5.30,28.25),(5.30,28.15))]:
    add_track("3V3", "B", p, q)
add_via("3V3", (5.30,28.15))
add_track("3V3", "I2", (5.30,28.15), (6.10,28.60))
add_track("3V3", "I2", (6.10,28.60), (6.60,29.45))
# 3V3 jog at R5.1
for (p, q) in [((4.40,35.15),(4.50,35.10)), ((4.50,35.10),(4.58,35.02)), ((4.58,35.02),(4.66,35.01))]:
    add_track("3V3", "B", p, q)
# 3V3_BAT vias
add_via("3V3_BAT", (3.66,33.02))
add_track("3V3_BAT", "B", (3.66,33.02), (3.55,32.40))
add_track("3V3_BAT", "I2", (4.75,33.70), (3.66,33.02))
add_via("3V3_BAT", (6.90,36.10))
add_track("3V3_BAT", "B", (6.90,36.10), (8.00,36.05))
add_track("3V3_BAT", "I2", (6.85,35.90), (6.90,36.10))
# PR1 via
add_via("PR1", (3.70,36.30))
add_track("PR1", "I2", (3.70,36.30), (4.95,36.25))
add_track("PR1", "B", (4.10,36.00), (3.70,36.30))
# VBAT via
add_via("VBAT", (12.30,31.85))
add_track("VBAT", "F", (11.90,31.55), (12.30,31.85))
add_track("VBAT", "I2", (12.30,31.85), (12.45,31.30))
# PR1 hand route
for (p, q) in [((4.50,29.56),(4.50,28.25)), ((4.50,28.25),(2.95,28.25))]:
    add_track("PR1", "B", p, q)
add_via("PR1", (2.95,28.25))
for (p, q) in [((2.95,28.25),(2.30,28.25)), ((2.30,28.25),(2.30,29.60)), ((2.30,29.60),(1.95,29.90)), ((1.95,29.90),(1.88,30.05))]:
    add_track("PR1", "I2", p, q)
add_via("PR1", (1.88,30.05))
for (p, q) in [((1.88,30.05),(2.20,30.20)), ((2.20,30.20),(2.20,35.60)), ((2.20,35.60),(3.30,35.75)), ((3.30,35.75),(3.95,36.45))]:
    add_track("PR1", "B", p, q)
add_via("PR1", (3.95,36.45))
add_track("PR1", "I2", (3.95,36.45), (4.60,37.00))
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX2V2 DONE")
