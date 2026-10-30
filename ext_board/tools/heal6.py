#!/usr/bin/env python3
"""Heal v6: for every DRC unconnected pair (JLEG pad, Track of same net,
any length), bridge pad centre -> closest point on the net's best nearby
segment. Tries the fragment's layer first, then the other layers (the
JLEG pads are TH, so any layer can join). Model-checked per layer.
Usage: heal6.py /path/to/drc.json"""
import pcbnew, os, sys, math, json, re
import importlib.util

DRC_JSON = sys.argv[1] if len(sys.argv) > 1 else "/tmp/drc_drive.json"
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["heal6"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LAYMAP = {"F.Cu": 0, "In2.Cu": 1, "B.Cu": 2}
JLEG = {
    "GPIO0": (16.67, 1.59), "GPIO1": (16.67, 4.13), "GPIO2": (16.67, 6.67),
    "GPIO3": (16.67, 9.21), "GPIO4": (16.67, 11.75), "GPIO5": (16.67, 14.29),
    "GPIO6": (16.67, 16.83), "GPIO7": (16.67, 19.37), "GPIO8": (16.67, 21.91),
    "GPIO9": (14.08, 21.96), "GPIO10": (11.54, 21.96), "GPIO11": (9.0, 21.96),
    "GPIO12": (6.46, 21.96), "GPIO13": (3.92, 21.96), "GPIO14": (1.33, 21.91),
    "GPIO15": (1.33, 19.37), "GPIO26": (1.33, 16.83), "GPIO27": (1.33, 14.29),
    "GPIO28": (1.33, 11.75), "GPIO29": (1.33, 9.21), "3V3": (1.33, 6.67),
    "VSYS": (1.33, 1.59),
}

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
    d = json.load(open(DRC_JSON))
    targets = {}
    for it in d["unconnected_items"]:
        items = it["items"]
        if len(items) != 2:
            continue
        descs = [i["description"] for i in items]
        pad_item = next((x for x in descs if "of JLEG" in x), None)
        trk_item = next((x for x in descs if x.startswith("Track")), None)
        if not pad_item or not trk_item:
            continue
        m = re.search(r"\[([^\]]+)\]", trk_item)
        lm = re.search(r"on (\S+),", trk_item)
        if m and lm and m.group(1) in JLEG:
            targets[m.group(1)] = LAYMAP[lm.group(1)]
    print("heal6 targets:", targets)
    if not targets:
        return
    b = pcbnew.LoadBoard(PATH)
    all_tracks = list(b.GetTracks())
    r = rt.R(b)
    r.ingest()
    for net, fragL in targets.items():
        px, py = JLEG[net]
        nid = r.net_ids[net]
        done = False
        for L in [fragL] + [x for x in (0, 1, 2) if x != fragL]:
            if done:
                break
            best = None
            for t in all_tracks:
                if t.GetNetname() != net or t.GetClass() == "PCB_VIA":
                    continue
                if {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}.get(t.GetLayer()) != L:
                    continue
                s = t.GetStart(); e = t.GetEnd()
                a = (pcbnew.ToMM(s.x), pcbnew.ToMM(s.y))
                c = (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))
                mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
                if math.hypot(mx - px, my - py) > 3.5:
                    continue
                dist, q = d_pt_seg((px, py), a, c)
                cand = (seg_len(t), dist, q)
                if best is None or (cand[0] > 0.3 and (best[0] <= 0.3 or cand[1] < best[1])) or (best[0] <= 0.3 and cand[0] > best[0]):
                    best = cand
            if best is None:
                continue
            _, dist, q = best
            steps = max(2, int(math.hypot(px - q[0], py - q[1]) / 0.05))
            ok = True
            for i in range(steps + 1):
                tt = i / steps
                sx, sy = q[0] + (px - q[0]) * tt, q[1] + (py - q[1]) * tt
                gx, gy = int(round(sx / 0.05)), int(round(sy / 0.05))
                if not (0 <= gx < 361 and 0 <= gy < 871) or not r.track_free(L, gy, gx, nid):
                    ok = False
                    break
            if not ok:
                continue
            t2 = pcbnew.PCB_TRACK(b)
            t2.SetStart(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])))
            t2.SetEnd(pcbnew.VECTOR2I(MM(px), MM(py)))
            t2.SetWidth(MM(0.10))
            t2.SetLayer(LAYERS[L])
            t2.SetNet(b.FindNet(net))
            b.Add(t2)
            r._stamp_track(L, q, (px, py), nid)
            r.rebuild_blockers()
            print(net, "bridge drawn on layer", L, "dist", round(dist, 2))
            done = True
        if not done:
            print(net, "no bridge possible on any layer")
    pcbnew.SaveBoard(PATH, b)
    print("HEAL6 DONE")

if __name__ == "__main__":
    main()
