#!/usr/bin/env python3
"""Hand-route the nets the stock router could not finish (REV.B plan v5).
Obstacles are rebuilt from the CURRENT board; every segment/via is validated
with exact geometry (capsule/rect/circle distances) before insertion.
DRC remains the final judge."""
import pcbnew, math, sys

TM = pcbnew.ToMM
FROMMM = pcbnew.FromMM
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

def seg_pt_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)

def seg_seg_dist(a, b, c, d):
    def orient(p, q, r): return (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])
    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    if (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0): return 0.0
    return min(seg_pt_dist(a, c, d), seg_pt_dist(b, c, d), seg_pt_dist(c, a, b), seg_pt_dist(d, a, b))

def seg_rect_dist(a, b, rect):
    x0, y0, x1, y1 = rect
    def inside(p): return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    if inside(a) or inside(b): return 0.0
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return min(seg_seg_dist(a, b, e0, e1) for e0, e1 in edges)

def load_obstacles(board, own_net):
    pads, tracks, vias = [], [], []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetname()
            if net == own_net: continue
            lay = pad.GetLayerSet()
            bb = pad.GetBoundingBox()
            rect = (TM(bb.GetLeft()), TM(bb.GetTop()), TM(bb.GetRight()), TM(bb.GetBottom()))
            for L in CU:
                if lay.Contains(L): pads.append((L, rect, net, fp.GetReference() + "." + pad.GetNumber()))
    for t in board.GetTracks():
        net = t.GetNetname()
        if net == own_net: continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            vias.append(((TM(p.x), TM(p.y)), TM(t.GetWidth()) / 2.0, net))
        else:
            a, c = t.GetStart(), t.GetEnd()
            tracks.append((t.GetLayer(), (TM(a.x), TM(a.y)), (TM(c.x), TM(c.y)), TM(t.GetWidth()) / 2.0, net))
    return pads, tracks, vias

def check_seg(obs, layer, a, b, hw, label):
    pads, tracks, vias = obs
    bad = []
    for (L, rect, net, ref) in pads:
        if L != layer: continue
        d = seg_rect_dist(a, b, rect)
        if d < hw + 0.10 - 1e-9: bad.append(f"pad {ref}[{net}] d={d:.3f}")
    for (L, ta, tb, thw, net) in tracks:
        if L != layer: continue
        d = seg_seg_dist(a, b, ta, tb)
        if d < hw + thw + 0.10 - 1e-9: bad.append(f"track[{net}] d={d:.3f}")
    for (pos, r, net) in vias:
        d = seg_pt_dist(pos, a, b)
        if d < hw + r + 0.10 - 1e-9: bad.append(f"via[{net}] d={d:.3f}")
    if bad: print(f"  !! {label}: " + "; ".join(bad[:5]))
    return not bad

def check_via(obs, pos, label):
    pads, tracks, vias = obs
    bad = []
    for (L, rect, net, ref) in pads:
        x0, y0, x1, y1 = rect
        dx = max(x0 - pos[0], 0, pos[0] - x1); dy = max(y0 - pos[1], 0, pos[1] - y1)
        d = math.hypot(dx, dy)
        if d < 0.30 - 1e-9: bad.append(f"pad {ref}[{net}] d={d:.3f}")
    for (L, ta, tb, thw, net) in tracks:
        d = seg_pt_dist(pos, ta, tb)
        if d < 0.20 + thw + 0.10 - 1e-9: bad.append(f"track[{net}] d={d:.3f}")
    for (vp, r, net) in vias:
        d = math.hypot(pos[0] - vp[0], pos[1] - vp[1])
        if d < 0.50 - 1e-9: bad.append(f"via[{net}] d={d:.3f}")
    if bad: print(f"  !! via {label}: " + "; ".join(bad[:5]))
    return not bad

def add_route(board, netname, layer, pts, width):
    net = board.GetNetInfo().GetNetItem(netname)
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(FROMMM(a[0]), FROMMM(a[1])))
        t.SetEnd(pcbnew.VECTOR2I(FROMMM(b[0]), FROMMM(b[1])))
        t.SetLayer(layer); t.SetWidth(FROMMM(width)); t.SetNet(net)
        board.Add(t)

def add_via(board, netname, pos):
    net = board.GetNetInfo().GetNetItem(netname)
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(FROMMM(pos[0]), FROMMM(pos[1])))
    v.SetWidth(FROMMM(0.40)); v.SetDrill(FROMMM(0.20))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net); board.Add(v)

F = pcbnew.F_Cu; B = pcbnew.B_Cu; I2 = pcbnew.In2_Cu

ROUTES = []
# ---- 3V3 path A: U4.2 -> B east along y28.3-28.8 -> W web (6.80,26.05)
ROUTES.append(("3V3", [
    ("seg", B, [(3.5,29.56),(3.5,28.80),(4.90,28.55),(5.35,28.30),(5.90,28.45),(6.35,28.55),(6.60,27.80),(6.64,26.90),(6.80,26.05)], 0.15),
]))
# ---- 3V3 path B: U4.7 -> B south -> east along y34-35 -> NE -> north ring via (10.00,19.60)
ROUTES.append(("3V3", [
    ("seg", B, [(3.5,31.04),(3.5,32.20),(3.85,32.95),(3.92,34.30),(4.60,34.75),(5.45,35.35),(6.30,34.80),(7.00,34.30),(7.60,34.30),(8.45,33.90),(8.55,31.90),(8.90,30.40),(9.40,28.60),(9.90,26.50),(10.00,24.50),(10.00,19.60)], 0.15),
    ("via", (10.00,19.60)),
    ("seg", I2, [(10.00,19.60),(10.15,18.49)], 0.15),
]))
# ---- VBAT: SW1.2 -> south band -> x10.04 channel -> east cluster via (12.05,31.75)
ROUTES.append(("VBAT", [
    ("seg", B, [(3.15,34.80),(3.30,35.95),(4.05,36.55),(4.90,35.90),(5.30,35.80),(5.90,36.25),(6.60,35.50),(7.30,35.60),(8.35,36.30),(8.50,34.45),(9.30,34.10),(10.04,34.45)], 0.15),
    ("seg", B, [(10.04,34.45),(10.04,36.85)], 0.15),
    ("seg", B, [(10.04,36.85),(11.90,36.90),(12.60,35.20),(13.00,33.80),(12.05,31.75)], 0.15),
]))

def main():
    board = pcbnew.LoadBoard("../ext_board_revb.kicad_pcb")
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for netname, steps in ROUTES:
        if only and netname != only: continue
        obs = load_obstacles(board, netname)
        print(f"== {netname}")
        ok = True
        for st in steps:
            if st[0] == "via":
                if not check_via(obs, st[1], f"{netname}@{st[1]}"): ok = False
            else:
                _, layer, pts, w = st
                for a, b in zip(pts, pts[1:]):
                    if not check_seg(obs, layer, a, b, w / 2.0, f"{netname} {a}->{b}"): ok = False
        if not ok:
            print(f"  {netname}: VALIDATION FAILED - not inserted"); continue
        for st in steps:
            if st[0] == "via": add_via(board, netname, st[1])
            else: add_route(board, netname, st[1], st[2], st[3])
        print(f"  {netname}: inserted")
        f = pcbnew.ZONE_FILLER(board); f.Fill(board.Zones())
        pcbnew.SaveBoard("../ext_board_revb.kicad_pcb", board)
        print("  SAVED")

if __name__ == "__main__":
    main()
