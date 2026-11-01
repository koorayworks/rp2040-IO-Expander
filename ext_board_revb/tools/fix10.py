#!/usr/bin/env python3
"""fix10 (base = fix4 state): 3V3 v13b, PR1 v16, PR1 S via (3.81,36.24), 3V3_BAT via."""
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
    ("3V3", (4.55,28.25), (4.72,28.85)), ("3V3", (4.72,28.85), (5.32,28.85)),
    ("3V3", (5.32,28.85), (5.32,29.30)), ("3V3", (5.32,29.30), (7.00,29.30)),
    ("3V3", (7.00,29.30), (7.20,29.60)), ("3V3", (7.20,29.60), (7.20,30.35)),
    ("PR1", (4.50,29.56), (5.08,29.56)), ("PR1", (5.08,29.56), (5.08,30.80)),
    ("PR1", (5.08,30.80), (5.24,31.60)), ("PR1", (5.24,31.60), (5.24,35.90)),
    ("PR1", (5.24,35.90), (4.55,35.95)),
    ("PR1", (3.85,36.30), (4.95,36.25)), ("PR1", (4.10,36.00), (3.85,36.30)),
    ("3V3_BAT", (3.95,33.05), (3.70,32.60)), ("3V3_BAT", (3.70,32.60), (3.55,32.40)),
    ("3V3_BAT", (4.75,33.70), (3.95,33.05)),
]
VIA_DELS = [("PR1", (3.85,36.30)), ("3V3_BAT", (3.95,33.05))]

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

def add_via(net, p):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(MM(0.20)); v.SetWidth(MM(0.40)); v.SetNet(b.FindNet(net))
    b.Add(v)

# 3V3 v13b: shifted dip, x5.18 south, SE window into web
for (p, q) in [((4.55,28.25),(4.60,28.60)), ((4.60,28.60),(5.18,28.90)), ((5.18,28.90),(5.18,33.60)),
               ((5.18,33.60),(5.48,34.45)), ((5.48,34.45),(5.48,34.80)), ((5.48,34.80),(4.95,34.80)),
               ((4.95,34.80),(4.95,34.55))]:
    add_track("3V3", "B", p, q)
# PR1 v16
for (p, q) in [((4.50,29.56),(4.50,29.05)), ((4.50,29.05),(4.90,28.62)), ((4.90,28.62),(5.35,28.38)),
               ((5.35,28.38),(5.90,28.55)), ((5.90,28.55),(5.95,28.60)), ((5.95,28.60),(6.20,29.60)),
               ((6.20,29.60),(6.28,29.75)), ((6.28,29.75),(6.28,32.50)), ((6.28,32.50),(6.50,31.85)),
               ((6.50,31.85),(7.48,32.38)), ((7.48,32.38),(6.60,34.00)), ((6.60,34.00),(6.00,34.65)),
               ((6.00,34.65),(5.65,34.95)), ((5.65,34.95),(5.30,35.50))]:
    add_track("PR1", "B", p, q)
# PR1 south via move
add_via("PR1", (3.81,36.24))
add_track("PR1", "I2", (3.81,36.24), (4.95,36.25))
add_track("PR1", "B", (4.10,36.00), (3.81,36.24))
# 3V3_BAT via move
add_via("3V3_BAT", (3.69,32.99))
add_track("3V3_BAT", "B", (3.69,32.99), (3.55,32.40))
add_track("3V3_BAT", "I2", (4.75,33.70), (3.69,32.99))
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX10 DONE")
