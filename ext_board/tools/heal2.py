#!/usr/bin/env python3
"""Heal v2: for the JLEG-adjacent nets whose first heal bridge fell short,
remove the previous bridge (track ending exactly at the pad centre) and
draw a new one from the CLOSEST POINT ON ANY SEGMENT of the net (interior
points allowed, T-junction) to the pad centre."""
import pcbnew, os, math, sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
TARGETS = {
    "GPIO3": (16.67, 9.21), "GPIO8": (16.67, 21.91), "GPIO9": (14.08, 21.96),
    "GPIO13": (3.92, 21.96), "GPIO28": (1.33, 11.75), "3V3": (1.33, 6.67),
}
sys.argv = ["heal2"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
LAYMAP = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}

def d_pt_seg(p, a, c):
    ax, ay = a; cx, cy = c; px, py = p
    dx, dy = cx - ax, cy - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    q = (ax + t * dx, ay + t * dy)
    return math.hypot(px - q[0], py - q[1]), q

def main():
    b = pcbnew.LoadBoard(PATH)
    all_tracks = list(b.GetTracks())
    r = rt.R(b)
    r.ingest()
    def tkey(t):
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            return ("V", p.x, p.y)
        st = t.GetStart(); en = t.GetEnd()
        return ("T", st.x, st.y, en.x, en.y, t.GetLayer())
    for net, (px, py) in TARGETS.items():
        nid = r.net_ids[net]
        net_obj = b.FindNet(net)
        # remove previous bridge: track of this net with an endpoint at pad centre
        for t in all_tracks:
            if t.GetNetname() != net or t.GetClass() == "PCB_VIA":
                continue
            for pt in (t.GetStart(), t.GetEnd()):
                if abs(pcbnew.ToMM(pt.x) - px) < 0.01 and abs(pcbnew.ToMM(pt.y) - py) < 0.01:
                    b.Remove(t)
                    g = r.geom.get(net)
                    if g:
                        g["objects"] = [o for o in g["objects"] if tkey(o) != tkey(t)]
                    print(net, "removed old bridge")
                    break
        r.rebuild_copper()
        # find closest point on any segment (or via) of the net
        best = (9e9, None, None)
        for t in all_tracks:
            if t.GetNetname() != net:
                continue
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                q = (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
                d = math.hypot(q[0] - px, q[1] - py)
                for LL in (0, 1, 2):
                    if d < best[0]:
                        best = (d, q, LL)
            else:
                s = t.GetStart(); e = t.GetEnd()
                a = (pcbnew.ToMM(s.x), pcbnew.ToMM(s.y))
                c = (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))
                d, q = d_pt_seg((px, py), a, c)
                if d < best[0]:
                    best = (d, q, LAYMAP.get(t.GetLayer()))
        d, (ax, ay), LL = best
        print(net, "closest copper point:", (round(ax, 2), round(ay, 2)), "layer", LL, "dist", round(d, 3))
        steps = max(2, int(math.hypot(px - ax, py - ay) / 0.05))
        ok = True
        for i in range(steps + 1):
            tt = i / steps
            sx, sy = ax + (px - ax) * tt, ay + (py - ay) * tt
            cx, cy = int(round(sx / 0.05)), int(round(sy / 0.05))
            if not (0 <= cx < 361 and 0 <= cy < 871) or not r.track_free(LL, cy, cx, nid):
                ok = False
                break
        if not ok:
            print(net, "bridge blocked in model -- drawing anyway (verify with DRC)")
        t2 = pcbnew.PCB_TRACK(b)
        t2.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
        t2.SetEnd(pcbnew.VECTOR2I(MM(px), MM(py)))
        t2.SetWidth(MM(0.10))
        t2.SetLayer([pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu][LL])
        t2.SetNet(net_obj)
        b.Add(t2)
        r._stamp_track(LL, (ax, ay), (px, py), nid)
        r.rebuild_blockers()
        print(net, "bridge drawn")
    pcbnew.SaveBoard(PATH, b)
    print("HEAL2 DONE")

if __name__ == "__main__":
    main()
