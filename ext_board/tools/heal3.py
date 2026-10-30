#!/usr/bin/env python3
"""Heal v3: for the 6 nets with a (0.15mm fragment <-> pad) gap, delete the
zero-length track at the pad centre and bridge pad centre -> closest point
on the fragment track (interior point allowed)."""
import pcbnew, os, math, sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
TARGETS = {
    "GPIO3": (16.67, 9.21), "GPIO8": (16.67, 21.91), "GPIO9": (14.08, 21.96),
    "GPIO13": (3.92, 21.96), "GPIO28": (1.33, 11.75), "3V3": (1.33, 6.67),
}
sys.argv = ["heal3"]
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
    for net, (px, py) in TARGETS.items():
        net_obj = b.FindNet(net)
        # 1) delete zero-length tracks of this net
        for t in all_tracks:
            if t.GetNetname() == net and t.GetClass() != "PCB_VIA" and seg_len(t) < 0.01:
                b.Remove(t)
                g = r.geom.get(net)
                if g:
                    g["objects"] = [o for o in g["objects"] if tkey(o) != tkey(t)]
                print(net, "removed zero-length track")
        r.rebuild_copper()
        # 2) fragment: track of this net, len 0.05..0.30, within 2.5mm of pad centre
        frag = None
        for t in all_tracks:
            if t.GetNetname() != net or t.GetClass() == "PCB_VIA":
                continue
            L = seg_len(t)
            if not (0.05 <= L <= 0.30):
                continue
            s = t.GetStart(); e = t.GetEnd()
            mx, my = pcbnew.ToMM((s.x + e.x) // 2), pcbnew.ToMM((s.y + e.y) // 2)
            if math.hypot(mx - px, my - py) < 2.5:
                frag = t
                break
        if frag is None:
            print(net, "NO FRAGMENT FOUND")
            continue
        s = frag.GetStart(); e = frag.GetEnd()
        a = (pcbnew.ToMM(s.x), pcbnew.ToMM(s.y))
        c = (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))
        d, q = d_pt_seg((px, py), a, c)
        LL = LAYMAP.get(frag.GetLayer())
        print(net, "fragment", a, "->", c, "closest", (round(q[0], 2), round(q[1], 2)), "dist", round(d, 3), "layer", LL)
        t2 = pcbnew.PCB_TRACK(b)
        t2.SetStart(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])))
        t2.SetEnd(pcbnew.VECTOR2I(MM(px), MM(py)))
        t2.SetWidth(MM(0.10))
        t2.SetLayer([pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu][LL])
        t2.SetNet(net_obj)
        b.Add(t2)
        print(net, "bridge drawn")
    pcbnew.SaveBoard(PATH, b)
    print("HEAL3 DONE")

if __name__ == "__main__":
    main()
