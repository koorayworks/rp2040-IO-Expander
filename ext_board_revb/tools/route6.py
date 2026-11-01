import sys, shutil
import pcbnew
from pcbnew import VECTOR2I
FM = pcbnew.FromMM; TM = pcbnew.ToMM
WORK = "backups/board_route6.kicad_pcb"
shutil.copy("backups/board_route5.kicad_pcb", WORK)

def load_validator():
    src = open("route3.py").read()
    head = src.split("JOBS = [")[0]
    head = head.replace('SRC = "backups/board_micro9.kicad_pcb"', f'SRC = "{WORK}"')
    head = head.replace('if pd["multi"] or l in pd["lay"]:', 'if l in pd["lay"]:')
    g = {}
    exec(head, g)
    return g["validate"]

def T(l,x1,y1,x2,y2): return ("T",l,x1,y1,x2,y2)
def V(x,y): return ("V",x,y)
LAYV = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LAYN = {pcbnew.F_Cu:0, pcbnew.In2_Cu:1, pcbnew.B_Cu:2}

def apply_items(net, cands, deletions=()):
    b = pcbnew.LoadBoard(WORK)
    if deletions:
        todel = []
        for t in b.GetTracks():
            if t.GetClass()=="PCB_VIA": continue
            a,c = t.GetStart(), t.GetEnd()
            kk = (t.GetNetname(), LAYN.get(t.GetLayer()), round(TM(a.x),2),round(TM(a.y),2),round(TM(c.x),2),round(TM(c.y),2))
            kr = (kk[0],kk[1],kk[4],kk[5],kk[2],kk[3])
            if kk in deletions or kr in deletions: todel.append(t)
        print("  deleting", len(todel), "old items")
        for t in todel: b.Remove(t)
    nobj = b.FindNet(net)
    for cd in cands:
        if cd[0]=="T":
            _,l,x1,y1,x2,y2 = cd
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(VECTOR2I(FM(x1),FM(y1))); t.SetEnd(VECTOR2I(FM(x2),FM(y2)))
            t.SetWidth(FM(0.10)); t.SetLayer(LAYV[l]); t.SetNet(nobj); b.Add(t)
        else:
            _,x,y = cd
            v = pcbnew.PCB_VIA(b); v.SetPosition(VECTOR2I(FM(x),FM(y)))
            v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetDrill(FM(0.20)); v.SetWidth(FM(0.40))
            v.SetNet(nobj); b.Add(v)
    filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
    b.Save(WORK)

def step(name, net, cands, deletions=()):
    validate = load_validator()
    bad = validate(cands, net)
    print(name, "violations:", len(bad))
    for (ci,desc,d,req) in bad: print("   cand", ci, cands[ci], "vs", desc, f"dist {d:.3f} req {req:.2f}")
    if bad: print(name, "SKIPPED"); return False
    apply_items(net, cands, deletions)
    print(name, "APPLIED")
    return True

# S0: MODE_STAIR rework (move seg_a/seg_b north, extend seg_c)
DEL0 = {("3V3_USB",2,3.00,29.56,3.25,29.00),("3V3_USB",2,3.25,29.00,4.80,29.05),("3V3_USB",2,4.80,29.05,4.80,30.60)}
step("S0_MODE_STAIR", "3V3_USB",
     [T(2,3.06,29.56,3.20,28.35), T(2,3.20,28.35,4.80,28.40), T(2,4.80,28.40,4.80,30.60)], DEL0)
# S1: VIN1 v2 (east exit, land on STAIR vertical)
step("S1_VIN1", "3V3_USB",
     [T(2,3.50,31.04,4.40,30.90), T(2,4.40,30.90,5.10,31.30), T(2,5.10,31.30,5.00,31.85)])
# S2: PR1a v3 (south exit, I2 hop over TB3/EX1 area, land R5.1)
step("S2_PR1a", "PR1",
     [T(2,3.00,31.04,3.05,31.60), T(2,3.05,31.60,4.18,31.60), T(2,4.18,31.60,4.35,32.55),
      V(4.35,32.55),
      T(1,4.35,32.55,4.90,34.60), T(1,4.90,34.60,5.80,34.65),
      V(5.80,34.65),
      T(2,5.80,34.65,5.10,35.55)])
# S3: LEG (F grand tour)
step("S3_LEG", "3V3_USB",
     [T(2,6.64,20.50,6.50,19.60), V(6.50,19.60),
      T(0,6.50,19.60,7.45,20.40), T(0,7.45,20.40,7.30,21.02), T(0,7.30,21.02,7.73,21.50),
      T(0,7.73,21.50,7.73,25.90), T(0,7.73,25.90,7.40,26.30), T(0,7.40,26.30,7.40,30.20),
      V(7.40,30.20),
      T(2,7.40,30.20,7.40,32.90), T(2,7.40,32.90,7.60,35.55), T(2,7.60,35.55,7.20,35.65)])
# S4: VIN2 (via north of U4, I2 grand tour, drop at BAT via)
step("S4_VIN2", "3V3_BAT",
     [T(2,3.62,29.62,3.70,29.05), T(2,3.70,29.05,3.90,28.90), V(3.90,28.90),
      T(1,3.90,28.90,3.90,28.70), T(1,3.90,28.70,6.45,28.70), T(1,6.45,28.70,7.90,29.30),
      T(1,7.90,29.30,7.90,31.50), T(1,7.90,31.50,8.55,31.50), V(8.55,31.50),
      T(2,8.55,31.50,8.72,31.50)])
print("done")
