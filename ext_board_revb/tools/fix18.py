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
 # fix17 leg
 ("B","3V3_USB",6.64,20.50,8.00,21.55),("B","3V3_USB",8.00,21.55,7.95,24.00),("B","3V3_USB",7.95,24.00,7.90,27.10),
 ("I2","3V3_USB",7.90,27.10,7.90,29.20),("I2","3V3_USB",7.90,29.20,8.30,29.60),("I2","3V3_USB",8.30,29.60,8.30,32.00),
 ("I2","3V3_USB",8.30,32.00,9.35,32.35),("I2","3V3_USB",9.35,32.35,9.35,34.30),("I2","3V3_USB",9.35,34.30,7.90,35.00),
 ("B","3V3_USB",7.90,35.00,7.60,35.475),
 # fix17 VIN2
 ("B","3V3_BAT",3.50,29.56,3.50,28.86),("B","3V3_BAT",3.50,28.86,3.05,28.30),("B","3V3_BAT",3.05,28.30,3.05,27.50),
 ("B","3V3_BAT",3.05,27.50,4.60,27.52),("B","3V3_BAT",4.60,27.52,5.30,27.40),
 ("I2","3V3_BAT",5.30,27.40,6.35,28.25),("I2","3V3_BAT",6.35,28.25,6.38,29.60),("I2","3V3_BAT",6.38,29.60,7.70,30.10),
 ("I2","3V3_BAT",7.70,30.10,8.70,31.50),
 # fix17 MODE
 ("B","3V3_USB",3.00,29.56,3.05,28.75),("B","3V3_USB",3.05,28.75,3.85,28.62),("B","3V3_USB",3.85,28.62,4.88,28.82),
 ("B","3V3_USB",4.88,28.82,4.88,30.88),
 # fix17 VIN1
 ("B","3V3_USB",3.50,31.04,3.62,30.80),("B","3V3_USB",3.62,30.80,4.45,30.507),
 # fix17 VOUT7
 ("B","3V3",4.00,29.56,4.26,29.72),("B","3V3",4.26,29.72,4.82,30.45),("B","3V3",4.82,30.45,4.82,31.55),("B","3V3",4.82,31.55,4.12,31.38),
 # fix17 bridge
 ("B","3V3_USB",4.40,30.55,5.02,30.02),("B","3V3_USB",5.02,30.02,5.02,31.75),("B","3V3_USB",5.02,31.75,4.30,31.60),
 # fix17 PR1
 ("B","PR1",2.85,31.04,2.78,31.38),("B","PR1",2.78,31.38,2.80,32.08),("B","PR1",2.80,32.08,2.66,32.62),
 ("B","PR1",2.66,32.62,2.42,32.95),("B","PR1",2.42,32.95,2.35,33.80),("B","PR1",2.35,33.80,3.25,34.12),
 ("B","PR1",3.25,34.12,4.08,34.55),("B","PR1",4.08,34.55,4.35,35.00),("B","PR1",4.35,35.00,4.35,35.70),
 ("B","PR1",4.35,35.70,4.10,36.00),
 # chain trims
 ("B","3V3_BAT",3.60,31.90,3.85,31.65),("B","3V3_BAT",3.85,31.65,3.85,31.60),("B","3V3_BAT",3.85,31.60,3.90,31.55),
 # 3V3 web EX1-graze bits
 ("B","3V3",5.18,33.62,5.38,34.00),("B","3V3",5.38,34.00,5.40,34.10),
]
DEL_VIAS = [("3V3_USB",7.90,27.10),("3V3_USB",7.90,35.00),("3V3_BAT",5.30,27.40)]
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
 # LEG v5 (B only)
 ("B","3V3_USB",6.64,20.50,5.36,20.42),("B","3V3_USB",5.36,20.42,5.36,26.30),("B","3V3_USB",5.36,26.30,4.55,26.10),
 ("B","3V3_USB",4.55,26.10,4.50,27.50),("B","3V3_USB",4.50,27.50,4.65,28.60),("B","3V3_USB",4.65,28.60,4.72,29.60),
 ("B","3V3_USB",4.72,29.60,4.80,30.497),
 # R4 link
 ("B","3V3_USB",7.12,35.48,6.35,35.65),("B","3V3_USB",6.35,35.65,5.45,35.82),("B","3V3_USB",5.45,35.82,5.38,35.85),
 ("I2","3V3_USB",5.38,35.85,5.52,36.12),
 # VIN1 v4
 ("B","3V3_USB",3.50,31.04,3.64,30.84),("B","3V3_USB",3.64,30.84,3.88,30.40),("B","3V3_USB",3.88,30.40,4.45,30.543),
 # VOUT7 v6
 ("B","3V3",4.00,29.56,4.26,29.70),("B","3V3",4.26,29.70,4.45,30.02),("B","3V3",4.45,30.02,4.84,30.24),
 ("B","3V3",4.84,30.24,4.84,31.50),("B","3V3",4.84,31.50,4.12,31.35),
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
for s in ADD: add_seg(*s)
add_via("3V3_USB", 5.38, 35.85)
add_via("3V3_BAT", 5.65, 27.35)
print("added", len(ADD), "segs + 2 vias")
zf = pcbnew.ZONE_FILLER(b); zf.Fill(b.Zones())
b.Save("backups/board_micro9.kicad_pcb")
print("saved")
