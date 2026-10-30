#!/usr/bin/env python3
"""Heal v4 (model-checked):
- GPIO9: remove the F.Cu bridge that crosses GP21; draw a 2-segment F.Cu
  path from the known-good fragment point (12.93,20.55) via (13.3,20.8)
  to the pad centre (14.08,21.96), each segment model-checked.
- GPIO13: bridge pad centre (3.92,21.96) -> closest point on its 1.55mm
  In2 fragment, model-checked."""
import pcbnew, os, math, sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["heal4"]
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

def seg_len(t):
    s = t.GetStart(); e = t.GetEnd()
    return math.hypot(pcbnew.ToMM(e.x - s.x), pcbnew.ToMM(e.y - s.y))

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
    def remove(t):
        b.Remove(t)
        g = r.geom.get(t.GetNetname())
        if g:
            g["objects"] = [o for o in g["objects"] if tkey(o) != tkey(t)]
    def check_and_draw(net, a, c, LL):
        nid = r.net_ids[net]
        steps = max(2, int(math.hypot(c[0] - a[0], c[1] - a[1]) / 0.05))
        for i in range(steps + 1):
            tt = i / steps
            sx, sy = a[0] + (c[0] - a[0]) * tt, a[1] + (c[1] - a[1]) * tt
            cx, cy = int(round(sx / 0.05)), int(round(sy / 0.05))
            if not (0 <= cx < 361 and 0 <= cy < 871) or not r.track_free(LL, cy, cx, nid):
                print(net, "segment blocked at", (round(sx, 2), round(sy, 2)))
                return False
        t2 = pcbnew.PCB_TRACK(b)
        t2.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
        t2.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
        t2.SetWidth(MM(0.10))
        t2.SetLayer([pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu][LL])
        t2.SetNet(b.FindNet(net))
        b.Add(t2)
        r._stamp_track(LL, a, c, nid)
        r.rebuild_blockers()
        print(net, "segment drawn", a, "->", c, "layer", LL)
        return True
    # GPIO9: remove the crossing bridge (F track with an endpoint at pad centre)
    for t in all_tracks:
        if t.GetNetname() != "GPIO9" or t.GetClass() == "PCB_VIA":
            continue
        for pt in (t.GetStart(), t.GetEnd()):
            if abs(pcbnew.ToMM(pt.x) - 14.08) < 0.01 and abs(pcbnew.ToMM(pt.y) - 21.96) < 0.01:
                remove(t)
                print("GPIO9 removed crossing bridge")
                break
    r.rebuild_copper()
    ok = check_and_draw("GPIO9", (12.93, 20.55), (13.3, 20.8), 0)
    if ok:
        check_and_draw("GPIO9", (13.3, 20.8), (14.08, 21.96), 0)
    # GPIO13: bridge to its 1.55mm In2 fragment
    frag = None
    for t in all_tracks:
        if t.GetNetname() != "GPIO13" or t.GetClass() == "PCB_VIA":
            continue
        if abs(seg_len(t) - 1.55) < 0.05 and t.GetLayer() == pcbnew.In2_Cu:
            frag = t
            break
    if frag is not None:
        s = frag.GetStart(); e = frag.GetEnd()
        a = (pcbnew.ToMM(s.x), pcbnew.ToMM(s.y))
        c = (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))
        d, q = d_pt_seg((3.92, 21.96), a, c)
        print("GPIO13 fragment closest point:", (round(q[0], 2), round(q[1], 2)), "dist", round(d, 3))
        check_and_draw("GPIO13", q, (3.92, 21.96), 1)
    else:
        print("GPIO13 fragment not found")
    pcbnew.SaveBoard(PATH, b)
    print("HEAL4 DONE")

if __name__ == "__main__":
    main()
