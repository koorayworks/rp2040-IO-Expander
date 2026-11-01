#!/usr/bin/env python3
"""fix3: remove fix2's bad hand additions, add corrected routes."""
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
    # 3V3 jog + bad north route
    ("3V3", (3.31,31.05), (3.90,30.80)), ("3V3", (3.90,30.80), (3.90,30.05)),
    ("3V3", (3.90,30.05), (3.31,29.90)), ("3V3", (3.31,29.90), (3.50,29.75)),
    ("3V3", (3.50,28.25), (5.30,28.25)), ("3V3", (5.30,28.25), (5.30,28.15)),
    ("3V3", (5.30,28.15), (6.10,28.60)), ("3V3", (6.10,28.60), (6.60,29.45)),
    # PR1 v1 hand route
    ("PR1", (4.50,29.56), (4.50,28.25)), ("PR1", (4.50,28.25), (2.95,28.25)),
    ("PR1", (2.95,28.25), (2.30,28.25)), ("PR1", (2.30,28.25), (2.30,29.60)),
    ("PR1", (2.30,29.60), (1.95,29.90)), ("PR1", (1.95,29.90), (1.88,30.05)),
    ("PR1", (1.88,30.05), (2.20,30.20)), ("PR1", (2.20,30.20), (2.20,35.60)),
    ("PR1", (2.20,35.60), (3.30,35.75)), ("PR1", (3.30,35.75), (3.95,36.45)),
    ("PR1", (3.95,36.45), (4.60,37.00)),
    # 3V3_BAT via redo segs
    ("3V3_BAT", (6.90,36.10), (8.00,36.05)), ("3V3_BAT", (6.85,35.90), (6.90,36.10)),
]
VIA_DELS = [("3V3", (5.30,28.15)), ("PR1", (2.95,28.25)), ("PR1", (1.88,30.05)), ("PR1", (3.95,36.45)),
            ("3V3_BAT", (6.90,36.10)), ("3V3_BAT", (7.00,36.05))]
PATCHMAP = {"3V3": {(7.35,30.20):(7.32,30.24)}}

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

# 3V3 north route v2 (B only, joins existing stub (7.20,30.35))
for (p, q) in [((3.50,28.25),(5.25,28.25)), ((5.25,28.25),(5.28,28.90)), ((5.28,28.90),(6.15,28.90)),
               ((6.15,28.90),(6.40,28.40)), ((6.40,28.40),(7.20,28.40)), ((7.20,28.40),(7.20,30.35))]:
    add_track("3V3", "B", p, q)
# PR1 v6 east route
for (p, q) in [((4.50,29.56),(5.10,29.56)), ((5.10,29.56),(5.10,35.90)), ((5.10,35.90),(4.55,35.95))]:
    add_track("PR1", "B", p, q)
# 3V3_BAT via redo at (6.95,36.35)
add_via("3V3_BAT", (6.95,36.35))
add_track("3V3_BAT", "B", (6.95,36.35), (8.00,36.05))
add_track("3V3_BAT", "I2", (6.85,35.90), (6.95,36.35))
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX3 DONE")
