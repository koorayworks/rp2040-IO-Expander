#!/usr/bin/env python3
"""fix16: from micro9 original state. Rotate U4 to r90 (center unchanged),
delete grazed/dangling copper, add all designed links."""
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
            n = pad.GetNumber(); p = pad.GetPosition()
            e = EXPECT[n]
            good = pad.GetNetname() == e[0] and abs(TM(p.x)-e[1]) < 0.02 and abs(TM(p.y)-e[2]) < 0.02
            print(f"pad{n} [{pad.GetNetname()}] ({TM(p.x):.2f},{TM(p.y):.2f}) expect {e} -> {'OK' if good else 'MISMATCH'}")
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
    # 3V3 winding mid (vs VIN1 rect) + stub-end inside VIN1 rect
    ("3V3", (3.15,30.50), (3.20,30.55)), ("3V3", (3.20,30.55), (3.20,30.60)),
    ("3V3", (3.20,30.60), (3.25,30.60)), ("3V3", (3.25,30.60), (3.25,30.65)),
    ("3V3", (3.25,30.65), (3.35,30.75)), ("3V3", (3.35,30.75), (3.35,31.10)),
    ("3V3", (3.31,31.20), (3.52,31.20)),
    # 3V3 north stub horizontal
    ("3V3", (3.50,28.25), (4.55,28.25)),
    # 3V3_USB staircase bits in/near GND pad1 rect + north bits in VOUT pad7 rect
    ("3V3_USB", (3.90,29.70), (4.05,29.80)), ("3V3_USB", (4.05,29.80), (4.20,30.00)),
    ("3V3_USB", (4.20,30.00), (4.30,30.20)),
    ("3V3_USB", (4.35,30.40), (4.35,30.50)), ("3V3_USB", (4.35,30.50), (4.40,30.55)),
    ("3V3_USB", (4.40,30.55), (4.40,30.70)), ("3V3_USB", (4.40,30.70), (4.45,30.75)),
    ("3V3_USB", (4.45,31.30), (4.45,31.45)), ("3V3_USB", (4.30,31.60), (4.45,31.45)),
    # 3V3_BAT chain north graze segs (inside VOUT pad2 rect)
    ("3V3_BAT", (3.95,31.30), (3.95,31.35)), ("3V3_BAT", (3.90,31.40), (3.95,31.35)),
    ("3V3_BAT", (3.90,31.55), (3.90,31.40)),
]
to_delete = []
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA": continue
    if any(seg_is(t, n, p, q) for (n, p, q) in SEG_DELS): to_delete.append(t); continue
    a, c = ep(t)
    # box rule 1: 3V3 stub vertical x=3.50, y 28.2-29.8
    if t.GetNetname() == "3V3" and abs(a[0]-3.50) < 0.01 and abs(c[0]-3.50) < 0.01 and 28.2 < a[1] < 29.8 and 28.2 < c[1] < 29.8:
        to_delete.append(t); continue
    # box rule 2: 3V3 winding graze bits near VIN2 rect
    if t.GetNetname() == "3V3" and 3.30 < a[0] < 3.70 and 3.30 < c[0] < 3.70 and 29.15 < a[1] < 29.99 and 29.15 < c[1] < 29.99:
        to_delete.append(t); continue
    # box rule 3: 3V3_USB bits with both endpoints x~4.45, y 30.65-31.50 (inside GND rect)
    if t.GetNetname() == "3V3_USB" and 4.38 < a[0] < 4.52 and 4.38 < c[0] < 4.52 and 30.65 < a[1] < 31.50 and 30.65 < c[1] < 31.50:
        to_delete.append(t); continue
print("delete:", len(to_delete))
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
    # winding repair (3V3)
    ("3V3", "B", (3.15,30.50), (3.02,30.90)), ("3V3", "B", (3.02,30.90), (3.10,31.53)),
    ("3V3", "B", (3.10,31.53), (3.40,31.53)), ("3V3", "B", (3.40,31.53), (3.31,31.62)),
    # VOUT pad2 link
    ("3V3", "B", (3.31,31.75), (4.00,31.30)),
    # VOUT pad7 east loop
    ("3V3", "B", (4.00,29.56), (4.22,30.35)), ("3V3", "B", (4.22,30.35), (4.78,30.58)),
    ("3V3", "B", (4.78,30.58), (4.78,30.95)), ("3V3", "B", (4.78,30.95), (4.10,31.20)),
    # VIN1 link
    ("3V3_USB", "B", (3.50,31.04), (3.55,30.52)), ("3V3_USB", "B", (3.55,30.52), (4.33,30.19)),
    # MODE north route
    ("3V3_USB", "B", (3.00,29.56), (3.05,28.75)), ("3V3_USB", "B", (3.05,28.75), (3.85,28.62)),
    ("3V3_USB", "B", (3.85,28.62), (4.88,28.82)), ("3V3_USB", "B", (4.88,28.82), (4.88,30.88)),
    # staircase bridge (east of GND pad1)
    ("3V3_USB", "B", (4.30,30.20), (4.94,30.05)), ("3V3_USB", "B", (4.94,30.05), (4.94,31.65)),
    ("3V3_USB", "B", (4.94,31.65), (4.30,31.60)),
    # VIN2 north route + I2 to east cluster via
    ("3V3_BAT", "B", (3.50,29.56), (3.50,28.86)), ("3V3_BAT", "B", (3.50,28.86), (4.55,28.90)),
    ("3V3_BAT", "B", (4.55,28.90), (5.30,28.35)), ("3V3_BAT", "B", (5.30,28.35), (6.45,28.30)),
    ("3V3_BAT", "I2", (6.45,28.30), (8.70,31.50)),
    # PR1 west corridor
    ("PR1", "B", (2.85,31.04), (2.75,31.35)), ("PR1", "B", (2.75,31.35), (2.78,32.10)),
    ("PR1", "B", (2.78,32.10), (2.42,32.95)), ("PR1", "B", (2.42,32.95), (2.35,33.80)),
    ("PR1", "B", (2.35,33.80), (3.30,34.15)), ("PR1", "B", (3.30,34.15), (4.10,36.00)),
    # 3V3_USB leg from U2.5
    ("3V3_USB", "B", (6.64,20.50), (6.64,19.25)),
    ("3V3_USB", "I2", (6.64,19.25), (6.64,28.80)), ("3V3_USB", "I2", (6.64,28.80), (7.90,30.50)),
    ("3V3_USB", "I2", (7.90,30.50), (7.90,34.50)), ("3V3_USB", "I2", (7.90,34.50), (7.35,35.45)),
    ("3V3_USB", "I2", (7.35,35.45), (5.50,35.45)), ("3V3_USB", "I2", (5.50,35.45), (5.40,36.30)),
    ("3V3_USB", "I2", (5.40,36.30), (6.25,36.15)),
]
for (n, l, p, q) in ADDS: add_track(n, l, p, q)
add_via("3V3_BAT", (6.45,28.30))
add_via("3V3_USB", (6.64,19.25))
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX16 DONE")
