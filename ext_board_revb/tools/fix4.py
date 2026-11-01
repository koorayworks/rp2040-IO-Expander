#!/usr/bin/env python3
"""fix4: corrected hand routes round 3."""
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
    ("3V3", (3.50,28.25), (5.25,28.25)), ("3V3", (5.25,28.25), (5.28,28.90)),
    ("3V3", (5.28,28.90), (6.15,28.90)), ("3V3", (6.15,28.90), (6.40,28.40)),
    ("3V3", (6.40,28.40), (7.20,28.40)), ("3V3", (7.20,28.40), (7.20,30.35)),
    ("PR1", (4.50,29.56), (5.10,29.56)), ("PR1", (5.10,29.56), (5.10,35.90)),
    ("PR1", (5.10,35.90), (4.55,35.95)),
    ("PR1", (3.70,36.30), (4.95,36.25)), ("PR1", (4.10,36.00), (3.70,36.30)),
    ("VBAT", (11.80,31.55), (11.45,31.90)), ("VBAT", (11.80,31.55), (11.90,31.55)),
    ("VBAT", (11.90,31.55), (12.30,31.85)), ("VBAT", (12.30,31.85), (12.45,31.30)),
    ("VBAT", (11.65,31.40), (11.80,31.55)),
    ("3V3_BAT", (3.66,33.02), (3.55,32.40)), ("3V3_BAT", (4.75,33.70), (3.66,33.02)),
]
VIA_DELS = [("PR1", (3.70,36.30)), ("VBAT", (11.80,31.55)), ("VBAT", (12.30,31.85)),
            ("3V3_BAT", (3.66,33.02)), ("3V3", (7.35,30.20)), ("3V3", (3.10,31.85))]
PATCHMAP = {"3V3": {(3.10,31.85):(3.02,31.92), (3.31,31.85):(3.31,31.92)}}

to_delete, patches = [], []
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        if any(via_is(t, n, p) for (n, p) in VIA_DELS): to_delete.append(t)
        continue
    if any(seg_is(t, n, p, q) for (n, p, q) in SEG_DELS): to_delete.append(t); continue
    mp = PATCHMAP.get(t.GetNetname())
    if mp:
        a, c = ep(t)
        na = mp.get((round(a[0],2), round(a[1],2)))
        nc = mp.get((round(c[0],2), round(c[1],2)))
        if na or nc: patches.append((t, na or a, nc or c))
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

# 3V3 U4.2 route FINAL (dip south of USB_D+ via, east to stub (7.20,30.35))
for (p, q) in [((3.50,28.25),(4.55,28.25)), ((4.55,28.25),(4.72,28.85)), ((4.72,28.85),(5.32,28.85)),
               ((5.32,28.85),(5.32,29.30)), ((5.32,29.30),(7.00,29.30)), ((7.00,29.30),(7.20,29.60)),
               ((7.20,29.60),(7.20,30.35))]:
    add_track("3V3", "B", p, q)
add_via("3V3", (7.32,30.24))
add_via("3V3", (3.02,31.92))
# PR1 v6b: vertical x5.24 with jog
for (p, q) in [((4.50,29.56),(5.08,29.56)), ((5.08,29.56),(5.08,30.80)), ((5.08,30.80),(5.24,31.60)),
               ((5.24,31.60),(5.24,35.90)), ((5.24,35.90),(4.55,35.95))]:
    add_track("PR1", "B", p, q)
# PR1 via redo
add_via("PR1", (3.85,36.30))
add_track("PR1", "I2", (3.85,36.30), (4.95,36.25))
add_track("PR1", "B", (4.10,36.00), (3.85,36.30))
# VBAT single-via cluster
add_via("VBAT", (12.05,31.70))
add_track("VBAT", "F", (11.45,31.90), (11.90,31.55))
add_track("VBAT", "F", (11.90,31.55), (12.05,31.70))
add_track("VBAT", "I2", (12.05,31.70), (12.45,31.30))
add_track("VBAT", "B", (11.65,31.40), (12.05,31.70))
# 3V3_BAT via redo
add_via("3V3_BAT", (3.95,33.05))
add_track("3V3_BAT", "B", (3.95,33.05), (3.70,32.60))
add_track("3V3_BAT", "B", (3.70,32.60), (3.55,32.40))
add_track("3V3_BAT", "I2", (4.75,33.70), (3.95,33.05))
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX4 DONE")
