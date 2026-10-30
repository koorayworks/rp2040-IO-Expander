#!/usr/bin/env python3
"""Waypoint-guided routing: route pad0 -> waypoint(s) -> pad1 using
astar_fast legs, committing each leg. Waypoints are small disks (r=0.3mm)
of model-free cells on any layer.
Usage: guided.py NET wx,wy [wx,wy ...]"""
import pcbnew, os, sys, time, math
import importlib.util

TARGET_NET = sys.argv[1] if len(sys.argv) > 1 else None
WPS = []
for a in sys.argv[2:]:
    x, y = a.split(",")
    WPS.append((float(x), float(y)))
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["guided"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

def wp_cells(r, nid, wx, wy):
    out = {}
    gx, gy = int(round(wx / 0.05)), int(round(wy / 0.05))
    for L in range(3):
        cells = set()
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                if math.hypot(dx, dy) <= 6 and 0 <= gx + dx < 361 and 0 <= gy + dy < 871:
                    if r.track_free(L, gy + dy, gx + dx, nid):
                        cells.add((gy + dy, gx + dx))
        if cells:
            out[L] = cells
    return out

def main():
    name = TARGET_NET
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    if r.net_components(name) <= 1:
        print(f"{name}: already connected")
        return
    t0 = time.time()
    nid = r.net_ids[name]
    net_obj = b.FindNet(name)
    th = r.th_cells.get(name, set())
    pads = r.pad_groups[name]
    ends = [r.endpoint(name, p) for p in pads]
    # start from the pad whose endpoint is smallest (most constrained)
    ends.sort(key=lambda e: sum(len(cs) for cs in e.values()))
    cur = {L: set(cs) for L, cs in ends[0].items()}
    targets = []
    for (wx, wy) in WPS:
        wc = wp_cells(r, nid, wx, wy)
        if not wc:
            print(f"{name}: waypoint ({wx},{wy}) has NO free cells")
            return
        targets.append(wc)
    targets.append(ends[1])
    for i, tgt in enumerate(targets):
        path = r.astar_fast(nid, cur, [tgt], th, via_cost=2.0, max_exp=900000)
        if path is None:
            print(f"{name}: leg {i} FAILED ({time.time()-t0:.0f}s) -- board NOT saved")
            return
        r.commit(name, path, net_obj)
        for L, cells in tgt.items():
            cur.setdefault(L, set()).update(cells)
        for (L, y, x) in path:
            cur.setdefault(L, set()).add((y, x))
        print(f"{name}: leg {i} ok ({time.time()-t0:.0f}s)", flush=True)
    if r.net_components(name) <= 1:
        pcbnew.SaveBoard(PATH, b)
        print(f"{name}: OK guided ({time.time()-t0:.0f}s)")
    else:
        print(f"{name}: legs done but components={r.net_components(name)} -- board NOT saved")

if __name__ == "__main__":
    main()
