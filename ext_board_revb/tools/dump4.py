import pcbnew
TM = pcbnew.ToMM
b = pcbnew.LoadBoard("backups/board_micro9.kicad_pcb")
for fp in b.GetFootprints():
    if fp.GetReference() in ("SW1","R4","R5","J7","JLEG","U2","C2","U3"):
        p = fp.GetPosition()
        print(f"{fp.GetReference()} pos ({TM(p.x):.2f},{TM(p.y):.2f}) rot {fp.GetOrientationDegrees():.0f} layer {'B' if fp.IsFlipped() else 'F'}")
        for pad in fp.Pads():
            bb = pad.GetBoundingBox(); c = pad.GetPosition()
            print(f"  pad{pad.GetNumber()} [{pad.GetNetname()}] c ({TM(c.x):.2f},{TM(c.y):.2f}) rect ({TM(bb.GetLeft()):.2f},{TM(bb.GetTop()):.2f})-({TM(bb.GetRight()):.2f},{TM(bb.GetBottom()):.2f})")
