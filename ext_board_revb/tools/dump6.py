import pcbnew
TM = pcbnew.ToMM
b = pcbnew.LoadBoard("backups/board_micro9.kicad_pcb")
LAY = {pcbnew.F_Cu:"F", pcbnew.In1_Cu:"I1", pcbnew.In2_Cu:"I2", pcbnew.B_Cu:"B"}
def hits(ax,ay,cx,cy,x0,x1,y0,y1):
    return not (max(ax,cx) < x0 or min(ax,cx) > x1 or max(ay,cy) < y0 or min(ay,cy) > y1)
def dump(tag,x0,x1,y0,y1,layer):
    print(f"=== {tag} ===")
    for t in b.GetTracks():
        if LAY[t.GetLayer()] != layer: continue
        a,c = t.GetStart(), t.GetEnd()
        ax,ay,cx,cy = TM(a.x),TM(a.y),TM(c.x),TM(c.y)
        if hits(ax,ay,cx,cy,x0,x1,y0,y1):
            if t.GetClass()=="PCB_VIA": print(f"VIA [{t.GetNetname()}] ({ax:.2f},{ay:.2f})")
            else: print(f"[{t.GetNetname()}] ({ax:.2f},{ay:.2f})-({cx:.2f},{cy:.2f})")
dump("I2 x3.3-7.6 y29-36.6",3.3,7.6,29.0,36.6,"I2")
dump("B x6.5-10.5 y34.5-38.5",6.5,10.5,34.5,38.5,"B")
dump("I2 x6.5-10.5 y34.5-38.5",6.5,10.5,34.5,38.5,"I2")
print("=== U1 pads 37-56 ===")
for fp in b.GetFootprints():
    if fp.GetReference()=="U1":
        for pad in fp.Pads():
            n=int(pad.GetNumber())
            if 37<=n<=56:
                bb=pad.GetBoundingBox(); c=pad.GetPosition()
                print(f"U1.{n} [{pad.GetNetname()}] c ({TM(c.x):.2f},{TM(c.y):.2f}) rect ({TM(bb.GetLeft()):.2f},{TM(bb.GetTop()):.2f})-({TM(bb.GetRight()):.2f},{TM(bb.GetBottom()):.2f})")
