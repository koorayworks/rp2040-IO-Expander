#!/usr/bin/env python3
"""Hand-routing for PR1 / 3V3_USB / 3V3 with exact-geometry verification.

Every segment/via is tested against the current board obstacles
(solve_place model: pad bboxes, track capsules, via circles) with the
design rules: track 0.10 wide -> centerline clearance 0.15 to foreign
copper; via 0.40 -> center clearance 0.30 to foreign copper.
Dry-run by default; --commit adds the geometry and saves.
Also replaces the mux GND via/link (build.py's straight link grazes
U4.2's corner in the bbox model).
"""
import pcbnew, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp

BASE = sp.BASE
MM = pcbnew.FromMM; TM = pcbnew.ToMM
PATH = os.path.join(BASE, "ext_board_revb.kicad_pcb")
LAY = {"F": pcbnew.F_Cu, "In2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}

def seg_seg_dist(ax, ay, bx, by, cx, cy, dx, dy):
    # intersection test via orientations
    def orient(px, py, qx, qy, rx, ry):
        v = (qy - py) * (rx - qx) - (qx - px) * (ry - qy)
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else 2)
    def onseg(px, py, qx, qy, rx, ry):
        return min(px, rx) - 1e-9 <= qx <= max(px, rx) + 1e-9 and min(py, ry) - 1e-9 <= qy <= max(py, ry) + 1e-9
    o1, o2 = orient(ax, ay, bx, by, cx, cy), orient(ax, ay, bx, by, dx, dy)
    o3, o4 = orient(cx, cy, dx, dy, ax, ay), orient(cx, cy, dx, dy, bx, by)
    if o1 != o2 and o3 != o4: return 0.0
    if o1 == 0 and onseg(ax, ay, cx, cy, bx, by): return 0.0
    if o2 == 0 and onseg(ax, ay, dx, dy, bx, by): return 0.0
    if o3 == 0 and onseg(cx, cy, ax, ay, dx, dy): return 0.0
    if o4 == 0 and onseg(cx, cy, bx, by, dx, dy): return 0.0
    return min(sp.seg_pt_dist(ax, ay, bx, by, cx, cy), sp.seg_pt_dist(ax, ay, bx, by, dx, dy),
               sp.seg_pt_dist(cx, cy, dx, dy, ax, ay), sp.seg_pt_dist(cx, cy, dx, dy, bx, by))

class Tester:
    def __init__(self, board):
        self.obs, _ = sp.load_obstacles(board)
    def seg_ok(self, net, layer, a, b, verbose=False):
        ax, ay = a; bx, by = b
        worst = (9.9, None)
        for (kind, data, onet) in self.obs[layer]:
            if onet == net and net != "": continue
            if kind == "rect":
                dd = sp.seg_rect_dist(ax, ay, bx, by, data)
            elif kind == "circ":
                dd = sp.seg_pt_dist(ax, ay, bx, by, data[0], data[1]) - data[2]
            else:
                dd = seg_seg_dist(ax, ay, bx, by, data[0], data[1], data[2], data[3]) - data[4]
            if dd < worst[0]: worst = (dd, (kind, onet, data))
        ok = worst[0] >= 0.15 - 1e-9
        if verbose or not ok:
            print(f"    seg {layer} {a}->{b} net={net}: min {worst[0]:.3f} vs {worst[1]} -> {'OK' if ok else 'FAIL'}")
        return ok
    def via_ok(self, net, x, y, verbose=False):
        worst = (9.9, None)
        for layer in ("F", "In2", "B"):
            for (kind, data, onet) in self.obs[layer]:
                if onet == net and net != "": continue
                if kind == "rect":
                    dd = sp.pt_rect_dist(x, y, data)
                elif kind == "circ":
                    dd = math.hypot(x - data[0], y - data[1]) - data[2]
                else:
                    dd = sp.seg_pt_dist(data[0], data[1], data[2], data[3], x, y) - data[4]
                if dd < worst[0]: worst = (dd, (layer, kind, onet, data))
        ok = worst[0] >= 0.30 - 1e-9
        if verbose or not ok:
            print(f"    via ({x},{y}) net={net}: min {worst[0]:.3f} vs {worst[1]} -> {'OK' if ok else 'FAIL'}")
        return ok

# ---------------- route data (polylines per net; vias listed separately) ----
ROUTES = {
  "PR1": [
    ("B", [(6.34,31.25),(6.72,33.30),(7.84,33.90),(7.84,35.23)]),
    ("B", [(6.34,31.25),(6.05,32.90),(6.05,34.40),(4.95,34.75),(4.25,33.30),(3.95,31.85),(3.64,31.18)]),
  ],
  "3V3": [
    ("B", [(4.86,30.25),(6.34,30.25)]),
    ("B", [(4.86,30.25),(4.30,30.25),(4.30,28.60)]),
    ("In2", [(4.45,28.30),(4.45,25.30),(5.30,25.62)]),
    ("B", [(5.05,26.10),(5.30,25.62)]),  # placeholder, replaced by via pair below
  ],
  "3V3_USB": [
    ("B", [(7.20,20.50),(8.10,20.10),(8.80,20.60),(8.80,22.60),(8.15,23.58)]),
    ("In2", [(8.15,23.58),(7.85,24.60),(7.55,25.90),(7.30,27.30),(6.90,28.60),(5.95,28.95),(5.40,29.30),(5.45,30.10),(5.60,30.75)]),
    ("B", [(5.60,30.75),(6.34,30.75)]),
    ("B", [(6.10,20.65),(6.45,22.60),(6.30,24.60),(5.95,25.55),(5.30,26.30),(5.30,28.20),(4.45,28.95),(3.64,29.52)]),
    ("B", [(4.45,28.95),(4.10,29.85),(3.95,30.60),(4.30,31.90),(4.86,31.60),(4.86,31.25)]),
  ],
}
VIAS = [
  ("3V3", 4.45, 28.30),   # B->In2 for the VOUT detour
  ("3V3_USB", 8.15, 23.58),
  ("3V3_USB", 5.60, 30.75),
]
# 3V3 route fix: the (5.05,26.10) pieces are replaced by via (5.05,26.10)? No:
# In2 ends ON the existing 3V3 via (5.30,25.62); the B placeholder is dropped.
ROUTES["3V3"] = [r for r in ROUTES["3V3"] if not (r[0] == "B" and r[1][0] == (5.05,26.10))]
ROUTES["3V3"].append(("B", [(4.30,28.60),(4.45,28.30)]))

def main():
    commit = "--commit" in sys.argv
    b = pcbnew.LoadBoard(PATH)
    # ---- step 0: replace mux GND via/link ----
    tv = Tester(b)
    print("mux GND via (7.9,29.6):", tv.via_ok("GND", 7.9, 29.6, verbose=True))
    for a, bb in [((6.34,29.75),(7.30,29.15)), ((7.30,29.15),(7.90,29.60))]:
        tv.seg_ok("GND", "B", a, bb, verbose=True)
    if commit:
        kill = []
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                if abs(TM(p.x) - 7.34) < 0.05 and abs(TM(p.y) - 30.3) < 0.05 and t.GetNetname() == "GND":
                    kill.append(t)
            else:
                a = t.GetStart(); c = t.GetEnd()
                pa = (TM(a.x), TM(a.y)); pc = (TM(c.x), TM(c.y))
                if t.GetNetname() == "GND" and ((abs(pa[0]-6.34)<0.05 and abs(pa[1]-29.75)<0.05) or (abs(pc[0]-6.34)<0.05 and abs(pc[1]-29.75)<0.05)):
                    kill.append(t)
        for t in kill: b.Remove(t)
        print(f"removed {len(kill)} old GND via/link objects")
        gnd = b.FindNet("GND")
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(MM(7.9), MM(29.6)))
        v.SetWidth(MM(0.40)); v.SetDrill(MM(0.20))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
        for a, bb in [((6.34,29.75),(7.30,29.15)), ((7.30,29.15),(7.90,29.60))]:
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(pcbnew.VECTOR2I(MM(bb[0]), MM(bb[1])))
            t.SetWidth(MM(0.30)); t.SetLayer(pcbnew.B_Cu); t.SetNet(gnd); b.Add(t)
    # ---- steps 1..3: hand nets ----
    allok = True
    for net in ("PR1", "3V3", "3V3_USB"):
        print(f"== {net}")
        tv = Tester(b)
        netobj = b.FindNet(net)
        for (x, y) in [(vx, vy) for (vn, vx, vy) in VIAS if vn == net]:
            if not tv.via_ok(net, x, y, verbose=True): allok = False
        for (layer, pts) in ROUTES[net]:
            for a, bb in zip(pts, pts[1:]):
                if not tv.seg_ok(net, layer, a, bb, verbose=True): allok = False
        if commit:
            for (vn, vx, vy) in VIAS:
                if vn != net: continue
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy)))
                v.SetWidth(MM(0.40)); v.SetDrill(MM(0.20))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(netobj); b.Add(v)
            for (layer, pts) in ROUTES[net]:
                for a, bb in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(pcbnew.VECTOR2I(MM(bb[0]), MM(bb[1])))
                    t.SetWidth(MM(0.10)); t.SetLayer(LAY[layer]); t.SetNet(netobj); b.Add(t)
            print(f"  committed {net}")
    if commit:
        filler = pcbnew.ZONE_FILLER(b)
        filler.Fill(b.Zones())
        pcbnew.SaveBoard(PATH, b)
        print("SAVED")
    print("ALL OK" if allok else "SOME FAILED")

if __name__ == "__main__":
    main()
