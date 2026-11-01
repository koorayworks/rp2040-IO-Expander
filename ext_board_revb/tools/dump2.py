import pcbnew, sys
TM = pcbnew.ToMM
b = pcbnew.LoadBoard("backups/board_micro9.kicad_pcb")
LAY = {pcbnew.F_Cu:"F", pcbnew.In1_Cu:"I1", pcbnew.In2_Cu:"I2", pcbnew.B_Cu:"B"}
def dump_region(x0,x1,y0,y1,nets=None):
    for t in b.GetTracks():
        a,c = t.GetStart(), t.GetEnd()
        ax,ay,cx,cy = TM(a.x),TM(a.y),TM(c.x),TM(c.y)
        if nets and t.GetNetname() not in nets: continue
        if x0-0.01 <= ax <= x1+0.01 and y0-0.01 <= ay <= y1+0.01 and x0-0.01 <= cx <= x1+0.01 and y0-0.01 <= cy <= y1+0.01:
            if t.GetClass()=="PCB_VIA": print(f"VIA [{t.GetNetname()}] ({ax:.2f},{ay:.2f})")
            else: print(f"{LAY[t.GetLayer()]} [{t.GetNetname()}] ({ax:.2f},{ay:.2f})-({cx:.2f},{cy:.2f})")
print("=== U4 pads (r270, fix11 state) ===")
for fp in b.GetFootprints():
    if fp.GetReference()=="U4":
        print("U4 pos", TM(fp.GetPosition().x), TM(fp.GetPosition().y), "rot", fp.GetOrientationDegrees())
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            print(f" pad{pad.GetNumber()} [{pad.GetNetname()}] rect ({TM(bb.GetLeft()):.2f},{TM(bb.GetTop()):.2f})-({TM(bb.GetRight()):.2f},{TM(bb.GetBottom()):.2f})")
print("=== B tracks x2.2-5.6 y27.8-33.6 ===")
dump_region(2.2,5.6,27.8,33.6)
