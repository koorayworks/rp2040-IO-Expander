#!/usr/bin/env python3
"""fix17: base = fix11 state (board_before_fix12). Rotate U4 to r90,
delete grazed/dangling copper, add dump-verified links."""
import pcbnew, os
MM = pcbnew.FromMM; TM = pcbnew.ToMM
PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups/board_micro9.kicad_pcb")
b = pcbnew.LoadBoard(PATH)

EXPECT = {"1": ("GND", 4.50, 31.04), "2": ("3V3", 4.00, 31.04), "3": ("3V3_USB", 3.50, 31.04),
          "4": ("PR1", 3.00, 31.04), "5": ("3V3_USB", 3.00, 29.56), "6": ("3V3_BAT", 3.50, 29.56),
          "7": ("3V3", 4.00, 29.56), "8": ("", 4.50, 29.56)}
for fp in b.GetFootprints():
    if fp.GetReference() == "U4":
        fp.SetOrientationDegrees(90.0)
        ok = True
        for pad in fp.Pads():
            n = pad.GetNumber(); p = pad.GetPosition(); bb = pad.GetBoundingBox()
            e = EXPECT[n]
            good = pad.GetNetname() == e[0] and abs(TM(p.x)-e[1]) < 0.02 and abs(TM(p.y)-e[2]) < 0.02
            print(f"pad{n} [{pad.GetNetname()}] c({TM(p.x):.2f},{TM(p.y):.2f}) rect ({TM(bb.GetLeft()):.2f},{TM(bb.GetTop()):.2f})-({TM(bb.GetRight()):.2f},{TM(bb.GetBottom()):.2f}) {'OK' if good else 'MISMATCH'}")
            ok = ok and good
        assert ok, "pad map mismatch - abort"
print("U4 r90 pad map verified")

def ep(t):
    a, c = t.GetStart(), t.GetEnd()
    return (TM(a.x), TM(a.y)), (TM(c.x), TM(c.y))
def close(p, q, tol=0.011): return abs(p[0]-q[0]) < tol and abs(p[1]-q[1]) < tol
def seg_is(t, net, p, q):
    if t.GetClass() == "PCB_VIA" or t.GetNetname() != net: return False
    a, c = ep(t)
    return (close(a, p) and close(c, q)) or (close(a, q) and close(c, p))

SEG_DELS = [
    ("3V3", (3.40,29.90), (3.45,29.85)), ("3V3", (3.45,29.85), (3.45,29.80)),
    ("3V3", (3.31,31.05), (3.31,31.92)), ("3V3", (3.31,31.20), (3.52,31.20)),
    ("3V3", (3.50,29.75), (3.50,28.25)), ("3V3", (3.50,28.25), (4.55,28.25)),
    ("3V3", (4.55,28.25), (4.58,28.50)), ("3V3", (4.58,28.50), (4.95,28.90)),
    ("3V3", (4.95,28.90), (5.18,28.95)), ("3V3", (5.18,28.95), (5.18,33.62)),
    ("3V3_USB", (4.40,30.55), (4.40,30.70)), ("3V3_USB", (4.40,30.70), (4.45,30.75)),
    ("3V3_USB", (4.45,30.75), (4.45,30.80)), ("3V3_USB", (4.45,31.30), (4.45,31.45)),
    ("3V3_USB", (4.45,31.45), (4.30,31.60)),
    ("3V3_BAT", (3.95,31.30), (3.95,31.35)), ("3V3_BAT", (3.90,31.40), (3.95,31.35)),
    ("3V3_BAT", (3.90,31.55), (3.90,31.40)),
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
def add_via(net, p):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(MM(p[0]), MM(p[1])))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetDrill(MM(0.20)); v.SetWidth(MM(0.40))
    v.SetNet(b.FindNet(net))
    b.Add(v)

ADDS = [
    # VOUT pad2 link (from winding via node (3.02,31.92))
    ("3V3", "B", (3.02,31.92), (3.24,31.70)), ("3V3", "B", (3.24,31.70), (4.00,31.32)),
    # VOUT pad7 east loop
    ("3V3", "B", (4.00,29.56), (4.26,29.72)), ("3V3", "B", (4.26,29.72), (4.82,30.45)),
    ("3V3", "B", (4.82,30.45), (4.82,31.55)), ("3V3", "B", (4.82,31.55), (4.12,31.38)),
    # VIN1 link (lands on bridge seg_a)
    ("3V3_USB", "B", (3.50,31.04), (3.62,30.80)), ("3V3_USB", "B", (3.62,30.80), (4.45,30.507)),
    # MODE north route
    ("3V3_USB", "B", (3.00,29.56), (3.05,28.75)), ("3V3_USB", "B", (3.05,28.75), (3.85,28.62)),
    ("3V3_USB", "B", (3.85,28.62), (4.88,28.82)), ("3V3_USB", "B", (4.88,28.82), (4.88,30.88)),
    # staircase bridge (east of GND pad1)
    ("3V3_USB", "B", (4.40,30.55), (5.02,30.02)), ("3V3_USB", "B", (5.02,30.02), (5.02,31.75)),
    ("3V3_USB", "B", (5.02,31.75), (4.30,31.60)),
    # VIN2 west-north route + via + I2 east run
    ("3V3_BAT", "B", (3.50,29.56), (3.50,28.86)), ("3V3_BAT", "B", (3.50,28.86), (3.05,28.30)),
    ("3V3_BAT", "B", (3.05,28.30), (3.05,27.50)), ("3V3_BAT", "B", (3.05,27.50), (4.60,27.52)),
    ("3V3_BAT", "B", (4.60,27.52), (5.30,27.40)),
    ("3V3_BAT", "I2", (5.30,27.40), (6.35,28.25)), ("3V3_BAT", "I2", (6.35,28.25), (6.38,29.60)),
    ("3V3_BAT", "I2", (6.38,29.60), (7.70,30.10)), ("3V3_BAT", "I2", (7.70,30.10), (8.70,31.50)),
    # PR1 west corridor + south run
    ("PR1", "B", (2.85,31.04), (2.78,31.38)), ("PR1", "B", (2.78,31.38), (2.80,32.08)),
    ("PR1", "B", (2.80,32.08), (2.66,32.62)), ("PR1", "B", (2.66,32.62), (2.42,32.95)),
    ("PR1", "B", (2.42,32.95), (2.35,33.80)), ("PR1", "B", (2.35,33.80), (3.25,34.12)),
    ("PR1", "B", (3.25,34.12), (4.08,34.55)), ("PR1", "B", (4.08,34.55), (4.35,35.00)),
    ("PR1", "B", (4.35,35.00), (4.35,35.70)), ("PR1", "B", (4.35,35.70), (4.10,36.00)),
    # 3V3_USB leg from U2.5 (B east, via, I2 south-east, via, R4.1)
    ("3V3_USB", "B", (6.64,20.50), (8.00,21.55)), ("3V3_USB", "B", (8.00,21.55), (7.95,24.00)),
    ("3V3_USB", "B", (7.95,24.00), (7.90,27.10)),
    ("3V3_USB", "I2", (7.90,27.10), (7.90,29.20)), ("3V3_USB", "I2", (7.90,29.20), (8.30,29.60)),
    ("3V3_USB", "I2", (8.30,29.60), (8.30,32.00)), ("3V3_USB", "I2", (8.30,32.00), (9.35,32.35)),
    ("3V3_USB", "I2", (9.35,32.35), (9.35,34.30)), ("3V3_USB", "I2", (9.35,34.30), (7.90,35.00)),
    ("3V3_USB", "B", (7.90,35.00), (7.60,35.475)),
]
for (n, l, p, q) in ADDS: add_track(n, l, p, q)
add_via("3V3_BAT", (5.30,27.40))
add_via("3V3_USB", (7.90,27.10))
add_via("3V3_USB", (7.90,35.00))
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX17 DONE")
