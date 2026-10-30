#!/usr/bin/env python3
"""Heal hairline disconnects at the elliptical castellation (JLEG) pads.
All track lists are collected BEFORE any Remove() call (KiCad 8.0.9
pcbnew: GetTracks() iteration breaks after Remove)."""
import pcbnew, os, math, sys, json, subprocess
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["heal"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
LAYMAP = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}

def run_drc(board_path, out):
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, board_path],
                   capture_output=True)
    return json.load(open(out))

def main():
    drc = run_drc(PATH, "/tmp/drc_heal_in.json")
    targets = []
    for it in drc["unconnected_items"]:
        descs = [i["description"] for i in it["items"]]
        poss = [i["pos"] for i in it["items"]]
        if not any("Track [" in d and "length 0.0" in d for d in descs):
            continue
        for dsc, pos in zip(descs, poss):
            if "of JLEG" in dsc and "[" in dsc:
                net = dsc.split("[")[1].split("]")[0]
                targets.append((net, (pos["x"], pos["y"])))
    print("heal targets:", targets)
    b = pcbnew.LoadBoard(PATH)
    # collect everything up-front
    all_tracks = list(b.GetTracks())
    r = rt.R(b)
    r.ingest()
    # anchors per net from the pre-collected list
    anchors_by_net = {}
    for t in all_tracks:
        name = t.GetNetname()
        if not name:
            continue
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            anchors_by_net.setdefault(name, []).append((pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), None))
        else:
            for pt in (t.GetStart(), t.GetEnd()):
                anchors_by_net.setdefault(name, []).append(
                    (pcbnew.ToMM(pt.x), pcbnew.ToMM(pt.y), LAYMAP.get(t.GetLayer())))
    def tkey(t):
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            return ("V", p.x, p.y)
        st = t.GetStart(); en = t.GetEnd()
        return ("T", st.x, st.y, en.x, en.y, t.GetLayer())
    healed = []
    for net, (px, py) in targets:
        nid = r.net_ids[net]
        net_obj = b.FindNet(net)
        removed = set()
        for t in all_tracks:
            if t.GetNetname() != net or t.GetClass() == "PCB_VIA":
                continue
            st = t.GetStart(); en = t.GetEnd()
            length = math.hypot(pcbnew.ToMM(en.x - st.x), pcbnew.ToMM(en.y - st.y))
            mx, my = pcbnew.ToMM((st.x + en.x) // 2), pcbnew.ToMM((st.y + en.y) // 2)
            if length <= 0.09 and math.hypot(mx - px, my - py) < 2.5:
                b.Remove(t)
                removed.add(tkey(t))
                g = r.geom.get(net)
                if g:
                    g["objects"] = [o for o in g["objects"] if tkey(o) != tkey(t)]
        if removed:
            r.rebuild_copper()
        anchors = []
        for (ax, ay, L) in anchors_by_net.get(net, []):
            anchors.append((math.hypot(ax - px, ay - py), ax, ay, L))
        anchors.sort(key=lambda t: t[0])
        done = False
        for (dist, ax, ay, L) in anchors[:8]:
            layers_try = [L] if L is not None else [0, 1, 2]
            for LL in layers_try:
                steps = max(2, int(math.hypot(px - ax, py - ay) / 0.05))
                ok = True
                for i in range(steps + 1):
                    tt = i / steps
                    sx, sy = ax + (px - ax) * tt, ay + (py - ay) * tt
                    cx, cy = int(round(sx / 0.05)), int(round(sy / 0.05))
                    if not (0 <= cx < 361 and 0 <= cy < 871):
                        ok = False
                        break
                    if not r.track_free(LL, cy, cx, nid):
                        ok = False
                        break
                if not ok:
                    continue
                t2 = pcbnew.PCB_TRACK(b)
                t2.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
                t2.SetEnd(pcbnew.VECTOR2I(MM(px), MM(py)))
                t2.SetWidth(MM(0.10))
                t2.SetLayer([pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu][LL])
                t2.SetNet(net_obj)
                b.Add(t2)
                r._stamp_track(LL, (ax, ay), (px, py), nid)
                r.rebuild_blockers()
                anchors_by_net.setdefault(net, []).append((px, py, LL))
                healed.append((net, round(ax, 2), round(ay, 2), LL))
                done = True
                break
            if done:
                break
        print("heal", net, "OK" if done else "FAILED")
    pcbnew.SaveBoard(PATH, b)
    print("healed:", healed)
    print("HEAL DONE")

if __name__ == "__main__":
    main()
