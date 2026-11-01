import pcbnew, sys
TM = pcbnew.ToMM
b = pcbnew.LoadBoard("/tmp/r7.kicad_pcb")
LAY = {pcbnew.F_Cu: "F", pcbnew.In2_Cu: "I2", pcbnew.B_Cu: "B"}
x0, y0, x1, y1 = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
mode = sys.argv[5] if len(sys.argv) > 5 else "T"
def hit(ax, ay, bx, by):
    return not (max(ax, bx) < x0 or min(ax, bx) > x1 or max(ay, by) < y0 or min(ay, by) > y1)
if mode == "T":
    rows = []
    for t in b.GetTracks():
        a, c = t.GetStart(), t.GetEnd()
        if t.GetClass() == "PCB_VIA":
            x, y = TM(a.x), TM(a.y)
            if x0 <= x <= x1 and y0 <= y <= y1:
                rows.append((99, f"VIA {t.GetNetname()} ({x:.2f},{y:.2f})"))
        elif t.GetLayer() in LAY:
            ax, ay, bx, by = TM(a.x), TM(a.y), TM(c.x), TM(c.y)
            if hit(ax, ay, bx, by):
                rows.append((LAY[t.GetLayer()], f"{LAY[t.GetLayer()]} {t.GetNetname()} ({ax:.2f},{ay:.2f})-({bx:.2f},{by:.2f})"))
    for L in ("F", "I2", "B", 99):
        for k, s in rows:
            if k == L: print(s)
else:
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            r = (TM(bb.GetLeft()), TM(bb.GetTop()), TM(bb.GetRight()), TM(bb.GetBottom()))
            if hit(r[0], r[1], r[2], r[3]):
                lays = "".join(L for L, lc in (("F", pcbnew.F_Cu), ("B", pcbnew.B_Cu)) if pad.IsOnLayer(lc))
                print(f"{fp.GetReference()}.{pad.GetNumber()} net='{pad.GetNetname()}' rect=({r[0]:.2f},{r[1]:.2f})-({r[2]:.2f},{r[3]:.2f}) lay={lays}")
