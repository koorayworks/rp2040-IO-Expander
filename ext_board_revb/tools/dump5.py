import pcbnew
TM = pcbnew.ToMM
b = pcbnew.LoadBoard("backups/board_micro9.kicad_pcb")
LAY = {pcbnew.F_Cu:"F", pcbnew.In1_Cu:"I1", pcbnew.In2_Cu:"I2", pcbnew.B_Cu:"B"}
def seg_hits(ax,ay,cx,cy,x0,x1,y0,y1):
    return not (max(ax,cx) < x0 or min(ax,cx) > x1 or max(ay,cy) < y0 or min(ay,cy) > y1)
def dump_region(tag,x0,x1,y0,y1,layers):
    print(f"=== {tag} ===")
    for t in b.GetTracks():
        if LAY[t.GetLayer()] not in layers: continue
        a,c = t.GetStart(), t.GetEnd()
        ax,ay,cx,cy = TM(a.x),TM(a.y),TM(c.x),TM(c.y)
        if seg_hits(ax,ay,cx,cy,x0,x1,y0,y1):
            if t.GetClass()=="PCB_VIA": print(f"VIA [{t.GetNetname()}] ({ax:.2f},{ay:.2f})")
            else: print(f"{LAY[t.GetLayer()]} [{t.GetNetname()}] ({ax:.2f},{ay:.2f})-({cx:.2f},{cy:.2f})")
dump_region("B x6.3-9.0 y19.8-28.6",6.3,9.0,19.8,28.6,{"B"})
dump_region("I2 x7.6-13.2 y26.0-35.6",7.6,13.2,26.0,35.6,{"I2"})
print("=== U1 pads 24-36 + J5 ===")
for fp in b.GetFootprints():
    if fp.GetReference() in ("U1","J5"):
        for pad in fp.Pads():
            n = pad.GetNumber()
            if fp.GetReference()=="U1" and not (24 <= int(n) <= 36): continue
            bb = pad.GetBoundingBox(); c = pad.GetPosition()
            print(f"{fp.GetReference()}.{n} [{pad.GetNetname()}] c ({TM(c.x):.2f},{TM(c.y):.2f}) rect ({TM(bb.GetLeft()):.2f},{TM(bb.GetTop()):.2f})-({TM(bb.GetRight()):.2f},{TM(bb.GetBottom()):.2f})")
