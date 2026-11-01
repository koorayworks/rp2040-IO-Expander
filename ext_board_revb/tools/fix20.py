import pcbnew
FM = pcbnew.FromMM; TM = pcbnew.ToMM
B = "backups/board_micro9.kicad_pcb"
b = pcbnew.LoadBoard(B)
LAY = {"F": pcbnew.F_Cu, "I2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}
def key(t):
    a,c = t.GetStart(), t.GetEnd()
    return (t.GetNetname(), LAY_R[t.GetLayer()], round(TM(a.x),2), round(TM(a.y),2), round(TM(c.x),2), round(TM(c.y),2))
LAY_R = {v:k for k,v in LAY.items()}
REM = set()
def R(net,lay,x1,y1,x2,y2): REM.add((net,lay,x1,y1,x2,y2)); REM.add((net,lay,x2,y2,x1,y1))
def RV(net,x,y): REM.add((net,"VIA",x,y))
# leg v15
for s in [(6.64,20.20,7.90,20.22),(7.90,20.22,8.15,21.75),(8.15,21.75,8.40,22.10),(8.40,22.10,9.00,23.70),(9.00,23.70,9.00,26.40),(9.00,26.40,6.45,26.35),(6.45,26.35,6.55,26.85),(6.55,26.85,6.55,28.15),(6.55,28.15,5.65,32.40)]: R("3V3_USB","B",*s)
R("3V3_USB","I2",5.65,32.40,6.20,34.45); R("3V3_USB","I2",6.20,34.45,5.65,36.60); R("3V3_USB","I2",5.65,36.60,5.58,36.15); RV("3V3_USB",5.65,32.40)
# R4 link v5
R("3V3_USB","B",7.90,35.88,8.35,36.30); R("3V3_USB","B",8.35,36.30,8.35,37.75); R("3V3_USB","B",8.35,37.75,7.30,37.85); R("3V3_USB","I2",7.30,37.85,6.25,36.15); RV("3V3_USB",7.30,37.85)
# VIN1 v5 seg_b/c
R("3V3_USB","B",3.66,30.86,3.94,30.36); R("3V3_USB","B",3.94,30.36,4.45,30.54)
# VOUT7 v7 + VOUT link v2
R("3V3","B",3.85,29.71,3.79,30.51); R("3V3","B",3.79,30.51,3.92,31.15)
R("3V3","B",3.02,31.92,3.24,31.80); R("3V3","B",3.24,31.80,3.92,31.38)
# VIN2 v13 (net 3V3_BAT)
for s in [(3.50,29.56,3.50,28.86),(3.50,28.86,3.18,28.30),(3.35,27.45,4.60,26.80),(4.60,26.80,5.45,27.02),(5.45,27.02,6.22,27.38)]: R("3V3_BAT","B",*s)
R("3V3_BAT","B",3.18,28.30,3.50,28.86)  # dup-safe
R("3V3_BAT","I2",3.18,28.30,3.35,27.45); R("3V3_BAT","I2",6.22,27.38,6.90,27.85); R("3V3_BAT","I2",6.90,27.85,7.00,28.75); R("3V3_BAT","I2",7.00,28.75,7.20,30.05); R("3V3_BAT","I2",7.20,30.05,8.75,31.55); R("3V3_BAT","I2",8.75,31.55,8.70,31.50)
RV("3V3_BAT",3.18,28.30); RV("3V3_BAT",3.35,27.45); RV("3V3_BAT",6.22,27.38)
# PR1 v8
R("PR1","B",2.85,31.04,2.98,31.40); R("PR1","F",2.98,31.40,2.48,32.85); R("PR1","B",2.48,32.85,2.90,32.75); R("PR1","B",2.90,32.75,3.58,33.15); R("PR1","B",3.58,33.15,3.58,34.15); R("PR1","B",3.58,34.15,3.98,34.72); R("PR1","B",3.98,34.72,4.12,35.35); R("PR1","B",4.12,35.35,4.95,35.50); R("PR1","B",4.95,35.50,4.60,35.85)
RV("PR1",2.98,31.40); RV("PR1",2.48,32.85)
# staircase bits near pad7
R("3V3_USB","B",3.90,29.65,4.05,29.80); R("3V3_USB","B",4.05,29.80,4.20,29.95); R("3V3_USB","B",4.20,29.95,4.20,30.00); R("3V3_USB","B",4.20,30.00,4.25,30.05)
# MODE v4 seg_b
R("3V3_USB","B",2.90,30.30,3.35,30.75)
found=[]; miss=[]
tracks = list(b.GetTracks())
for t in tracks:
    if t.GetClass()=="PCB_VIA":
        a=t.GetStart(); k=(t.GetNetname(),"VIA",round(TM(a.x),2),round(TM(a.y),2))
        if k in REM: found.append(t)
    else:
        if key(t) in REM: found.append(t)
have = {key(t) for t in tracks if t.GetClass()!="PCB_VIA"} | {(t.GetNetname(),"VIA",round(TM(t.GetStart().x),2),round(TM(t.GetStart().y),2)) for t in tracks if t.GetClass()=="PCB_VIA"}
for r in REM:
    if r not in have and not (len(r)==4): miss.append(r)
print("remove found:", len(found), "missing segs:", [m for m in miss if len(m)==6])
for t in found: b.Remove(t)
def seg(net,lay,x1,y1,x2,y2):
    t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(FM(x1),FM(y1))); t.SetEnd(pcbnew.VECTOR2I(FM(x2),FM(y2)))
    t.SetWidth(FM(0.10)); t.SetLayer(LAY[lay]); t.SetNet(b.FindNet(net)); b.Add(t)
def via(net,x,y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(FM(x),FM(y))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(FM(0.20)); v.SetWidth(FM(0.40)); v.SetNet(b.FindNet(net)); b.Add(v)
# LEG v19
for s in [(6.95,20.20,7.95,19.75),(7.95,19.75,8.85,21.60),(8.85,21.60,9.05,26.10),(9.05,26.10,9.40,26.30),(9.40,26.30,9.40,27.60),(9.40,27.60,8.30,27.85),(8.30,27.85,7.78,29.08),(7.78,29.08,8.50,29.75),(8.50,29.75,8.50,32.90),(8.50,32.90,8.60,33.60),(8.60,33.60,7.60,35.55),(7.60,35.55,7.20,35.65)]: seg("3V3_USB","B",*s)
# R4 link v6
seg("3V3_USB","B",7.12,35.48,7.20,35.65)
# staircase reroute
seg("3V3_USB","B",3.90,29.65,4.02,30.02); seg("3V3_USB","B",4.02,30.02,4.30,30.30)
# VIN1 v6
seg("3V3_USB","B",3.66,30.86,3.90,30.33); seg("3V3_USB","B",3.90,30.33,4.45,30.54)
# MODE v5 seg_b
seg("3V3_USB","B",2.90,30.30,3.45,30.70)
# VOUT7 v10 + VOUT link v3
seg("3V3","B",3.85,29.71,3.76,31.05); seg("3V3","B",3.76,31.05,4.05,31.38)
seg("3V3","B",3.02,31.92,3.24,31.85); seg("3V3","B",3.24,31.85,3.92,31.38)
# VIN2 v16
for s in [(3.50,29.56,3.90,29.90),(3.90,29.90,4.35,29.85),(4.35,29.85,4.80,29.85),(4.80,29.85,4.80,31.58),(4.80,31.58,4.35,31.58)]: seg("3V3_BAT","B",*s)
via("3V3_BAT",4.35,31.58)
seg("3V3_BAT","I2",4.35,31.58,5.90,31.45); seg("3V3_BAT","I2",5.90,31.45,6.60,32.45)
via("3V3_BAT",6.60,32.45)
seg("3V3_BAT","B",6.60,32.45,6.60,32.15); seg("3V3_BAT","B",6.60,32.15,8.70,32.10); seg("3V3_BAT","B",8.70,32.10,8.70,31.50)
# PR1 v12
seg("PR1","B",2.85,31.04,3.95,31.85); seg("PR1","B",3.95,31.85,3.82,33.00); seg("PR1","B",3.82,33.00,4.55,33.40)
via("PR1",4.55,33.40)
seg("PR1","F",4.55,33.40,4.02,34.00); seg("PR1","F",4.02,34.00,3.95,36.10)
via("PR1",3.95,36.10)
seg("PR1","B",3.95,36.10,4.10,36.00)
filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
b.Save(B); print("fix20 applied+saved")
