import pcbnew
TM = pcbnew.ToMM
b = pcbnew.LoadBoard("backups/board_micro9.kicad_pcb")
LAY = {pcbnew.F_Cu:"F", pcbnew.In1_Cu:"I1", pcbnew.In2_Cu:"I2", pcbnew.B_Cu:"B"}
def dump_region(tag,x0,x1,y0,y1):
    print(f"=== {tag} ===")
    for t in b.GetTracks():
        a,c = t.GetStart(), t.GetEnd()
        ax,ay,cx,cy = TM(a.x),TM(a.y),TM(c.x),TM(c.y)
        if x0-0.01 <= ax <= x1+0.01 and y0-0.01 <= ay <= y1+0.01 and x0-0.01 <= cx <= x1+0.01 and y0-0.01 <= cy <= y1+0.01:
            if t.GetClass()=="PCB_VIA": print(f"VIA [{t.GetNetname()}] ({ax:.2f},{ay:.2f})")
            else: print(f"{LAY[t.GetLayer()]} [{t.GetNetname()}] ({ax:.2f},{ay:.2f})-({cx:.2f},{cy:.2f})")
dump_region("B winding mid x2.9-3.6 y29.9-31.3",2.9,3.6,29.9,31.3)
dump_region("I2 east x5.2-8.9 y26.4-33.6",5.2,8.9,26.4,33.6)
dump_region("B east x5.2-8.2 y26.8-33.0",5.2,8.2,26.8,33.0)
dump_region("PR1/SW1 south x2.2-5.8 y33.6-37.6",2.2,5.8,33.6,37.6)
