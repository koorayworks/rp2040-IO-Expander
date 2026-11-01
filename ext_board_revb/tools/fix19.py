import pcbnew
TM = pcbnew.ToMM; FM = pcbnew.FromMM
b = pcbnew.LoadBoard("backups/board_micro9.kicad_pcb")
LAY = {"F": pcbnew.F_Cu, "I2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}
def close(a, c, tol=0.02): return abs(a-c) <= tol
def seg_match(t, lay, net, ax, ay, cx, cy):
    if t.GetClass() == "PCB_VIA" or t.GetLayer() != LAY[lay] or t.GetNetname() != net: return False
    a, c = t.GetStart(), t.GetEnd()
    axx, ayy, cxx, cyy = TM(a.x), TM(a.y), TM(c.x), TM(c.y)
    return (close(axx,ax) and close(ayy,ay) and close(cxx,cx) and close(cyy,cy)) or \
           (close(axx,cx) and close(ayy,cy) and close(cxx,ax) and close(cyy,ay))
def via_match(t, net, x, y):
    if t.GetClass() != "PCB_VIA" or t.GetNetname() != net: return False
    p = t.GetPosition(); return close(TM(p.x), x) and close(TM(p.y), y)

DEL_SEGS = [
 # leg v5
 ("B","3V3_USB",6.64,20.50,5.36,20.42),("B","3V3_USB",5.36,20.42,5.36,26.30),("B","3V3_USB",5.36,26.30,4.55,26.10),
 ("B","3V3_USB",4.55,26.10,4.50,27.50),("B","3V3_USB",4.50,27.50,4.65,28.60),("B","3V3_USB",4.65,28.60,4.72,29.60),
 ("B","3V3_USB",4.72,29.60,4.80,30.497),
 # R4 link v1
 ("B","3V3_USB",7.12,35.48,6.35,35.65),("B","3V3_USB",6.35,35.65,5.45,35.82),("B","3V3_USB",5.45,35.82,5.38,35.85),
 ("I2","3V3_USB",5.38,35.85,5.52,36.12),
 # VIN1 v4
 ("B","3V3_USB",3.50,31.04,3.64,30.84),("B","3V3_USB",3.64,30.84,3.88,30.40),("B","3V3_USB",3.88,30.40,4.45,30.543),
 # VOUT7 v6 + VOUT link v1
 ("B","3V3",4.00,29.56,4.26,29.70),("B","3V3",4.26,29.70,4.45,30.02),("B","3V3",4.45,30.02,4.84,30.24),
 ("B","3V3",4.84,30.24,4.84,31.50),("B","3V3",4.84,31.50,4.12,31.35),
 ("B","3V3",3.02,31.92,3.24,31.70),("B","3V3",3.24,31.70,4.00,31.32),
 # bridge v7
 ("B","3V3_USB",4.40,30.55,4.92,30.48),("B","3V3_USB",4.92,30.48,5.06,30.60),("B","3V3_USB",5.06,30.60,5.06,31.75),
 ("B","3V3_USB",5.06,31.75,4.30,31.60),
 # MODE v2
 ("B","3V3_USB",3.00,29.56,3.05,28.75),("B","3V3_USB",3.05,28.75,3.85,28.62),("B","3V3_USB",3.85,28.62,4.42,28.72),
 ("B","3V3_USB",4.42,28.72,4.55,30.530),
 # VIN2 v7
 ("B","3V3_BAT",3.50,29.56,3.50,28.86),("B","3V3_BAT",3.50,28.86,3.28,28.15),("B","3V3_BAT",3.28,28.15,3.28,27.50),
 ("B","3V3_BAT",3.28,27.50,4.60,26.80),("B","3V3_BAT",4.60,26.80,5.45,27.22),("B","3V3_BAT",5.45,27.22,5.65,27.35),
 ("I2","3V3_BAT",5.65,27.35,6.02,28.75),("I2","3V3_BAT",6.02,28.75,6.90,29.70),("I2","3V3_BAT",6.90,29.70,7.70,30.05),
 ("I2","3V3_BAT",7.70,30.05,8.05,31.75),("I2","3V3_BAT",8.05,31.75,8.55,32.20),("I2","3V3_BAT",8.55,32.20,8.70,31.50),
 # PR1 v4
 ("B","PR1",2.85,31.04,2.76,31.40),("B","PR1",2.76,31.40,2.62,32.15),("B","PR1",2.62,32.15,2.20,32.24),
 ("B","PR1",2.20,32.24,2.35,33.80),("B","PR1",2.35,33.80,3.35,33.55),("B","PR1",3.35,33.55,4.05,33.75),
 ("B","PR1",4.05,33.75,4.10,34.15),("B","PR1",4.10,34.15,4.10,35.05),("B","PR1",4.10,35.05,4.28,35.60),
 ("B","PR1",4.28,35.60,4.40,36.00),
]
DEL_VIAS = [("3V3_USB",5.38,35.85),("3V3_BAT",5.65,27.35)]
tracks = list(b.GetTracks())
doomed = []
for spec in DEL_SEGS:
    hits = [t for t in tracks if seg_match(t, *spec)]
    assert len(hits) == 1, f"DEL {spec}: {len(hits)} hits"
    doomed.append(hits[0])
for spec in DEL_VIAS:
    hits = [t for t in tracks if via_match(t, *spec)]
    assert len(hits) == 1, f"DELVIA {spec}: {len(hits)} hits"
    doomed.append(hits[0])
for t in doomed: b.Remove(t)
print("removed", len(doomed))

def add_seg(lay, net, ax, ay, cx, cy):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(FM(ax), FM(ay))); t.SetEnd(pcbnew.VECTOR2I(FM(cx), FM(cy)))
    t.SetWidth(FM(0.10)); t.SetLayer(LAY[lay]); t.SetNet(b.FindNet(net)); b.Add(t)
def add_via(net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(FM(0.20)); v.SetWidth(FM(0.40)); v.SetNet(b.FindNet(net)); b.Add(v)

ADD = [
 # LEG v15
 ("B","3V3_USB",6.64,20.20,7.90,20.22),("B","3V3_USB",7.90,20.22,8.15,21.75),("B","3V3_USB",8.15,21.75,8.40,22.10),
 ("B","3V3_USB",8.40,22.10,9.00,23.70),("B","3V3_USB",9.00,23.70,9.00,26.40),("B","3V3_USB",9.00,26.40,6.45,26.35),
 ("B","3V3_USB",6.45,26.35,6.55,26.85),("B","3V3_USB",6.55,26.85,6.55,28.15),("B","3V3_USB",6.55,28.15,5.65,32.40),
 ("I2","3V3_USB",5.65,32.40,6.20,34.45),("I2","3V3_USB",6.20,34.45,5.65,36.60),("I2","3V3_USB",5.65,36.60,5.58,36.15),
 # R4 link v5
 ("B","3V3_USB",7.90,35.88,8.35,36.30),("B","3V3_USB",8.35,36.30,8.35,37.75),("B","3V3_USB",8.35,37.75,7.30,37.85),
 ("I2","3V3_USB",7.30,37.85,6.25,36.15),
 # VIN1 v5
 ("B","3V3_USB",3.50,31.04,3.66,30.86),("B","3V3_USB",3.66,30.86,3.94,30.36),("B","3V3_USB",3.94,30.36,4.45,30.543),
 # VOUT7 v7 + VOUT link v2
 ("B","3V3",3.85,29.71,3.79,30.51),("B","3V3",3.79,30.51,3.92,31.15),
 ("B","3V3",3.02,31.92,3.24,31.80),("B","3V3",3.24,31.80,3.92,31.38),
 # bridge v9
 ("B","3V3_USB",4.40,30.55,5.06,30.46),("B","3V3_USB",5.06,30.46,5.06,31.75),("B","3V3_USB",5.06,31.75,4.30,31.60),
 # MODE v4
 ("B","3V3_USB",3.00,29.56,2.90,30.30),("B","3V3_USB",2.90,30.30,3.35,30.75),
 # VIN2 v13
 ("B","3V3_BAT",3.50,29.56,3.50,28.86),("B","3V3_BAT",3.50,28.86,3.18,28.30),
 ("I2","3V3_BAT",3.18,28.30,3.35,27.45),
 ("B","3V3_BAT",3.35,27.45,4.60,26.80),("B","3V3_BAT",4.60,26.80,5.45,27.02),("B","3V3_BAT",5.45,27.02,6.22,27.38),
 ("I2","3V3_BAT",6.22,27.38,6.90,27.85),("I2","3V3_BAT",6.90,27.85,7.00,28.75),("I2","3V3_BAT",7.00,28.75,7.20,30.05),
 ("I2","3V3_BAT",7.20,30.05,8.75,31.55),("I2","3V3_BAT",8.75,31.55,8.70,31.50),
 # PR1 v8
 ("B","PR1",2.85,31.04,2.98,31.40),
 ("F","PR1",2.98,31.40,2.48,32.85),
 ("B","PR1",2.48,32.85,2.90,32.75),("B","PR1",2.90,32.75,3.58,33.15),("B","PR1",3.58,33.15,3.58,34.15),
 ("B","PR1",3.58,34.15,3.98,34.72),("B","PR1",3.98,34.72,4.12,35.35),("B","PR1",4.12,35.35,4.95,35.50),
 ("B","PR1",4.95,35.50,4.60,35.85),
]
for s in ADD: add_seg(*s)
add_via("3V3_USB", 5.65, 32.40)
add_via("3V3_USB", 7.30, 37.85)
add_via("3V3_BAT", 3.18, 28.30)
add_via("3V3_BAT", 3.35, 27.45)
add_via("3V3_BAT", 6.22, 27.38)
add_via("PR1", 2.98, 31.40)
add_via("PR1", 2.48, 32.85)
print("added", len(ADD), "segs + 7 vias")
zf = pcbnew.ZONE_FILLER(b); zf.Fill(b.Zones())
b.Save("backups/board_micro9.kicad_pcb")
print("saved")
