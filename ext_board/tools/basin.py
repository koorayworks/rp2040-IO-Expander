#!/usr/bin/env python3
"""Basin diagnostic: for each target net, flood-fill the router model from
each pad's member cells (through track_free cells + via_free layer hops)
and report basin size and the nets forming the basin boundary.
Usage: basin.py NET [NET ...]"""
import pcbnew, os, sys, time
import importlib.util
import numpy as np
from collections import deque, Counter

NAMES = sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["basin"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
CELL, W, H, NL = rt.CELL, rt.W, rt.H, rt.NL


def basin_of(r, name, rec):
    nid = r.net_ids[name]
    ep = r.endpoint(name, rec)
    seen = [np.zeros((H, W), dtype=bool) for _ in range(NL)]
    dq = deque()
    for L, cells in ep.items():
        for (y, x) in cells:
            if not seen[L][y, x]:
                seen[L][y, x] = True
                dq.append((L, y, x))
    th = r.th_cells.get(name, set())
    while dq:
        L, y, x = dq.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < W and 0 <= ny_ < H) or seen[L][ny_, nx_]:
                    continue
                if r.track_free(L, ny_, nx_, nid):
                    seen[L][ny_, nx_] = True
                    dq.append((L, ny_, nx_))
        for oL in range(NL):
            if oL == L or seen[oL][y, x]:
                continue
            if (y, x) in th or r.via_free(y, x, nid):
                seen[oL][y, x] = True
                dq.append((oL, y, x))
    return seen


def boundary_nets(r, name, seen):
    nid = r.net_ids[name]
    cnt = Counter()
    inv = {v: k for k, v in r.net_ids.items()}
    for L in range(NL):
        ys, xs = np.nonzero(seen[L])
        for y, x in zip(ys.tolist(), xs.tolist()):
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    nx_, ny_ = x + dx, y + dy
                    if 0 <= nx_ < W and 0 <= ny_ < H:
                        v = r.copper[L][ny_, nx_]
                        if v > 0 and v != nid:
                            cnt[inv.get(v, str(v))] += 1
    return cnt.most_common(8)


def main():
    names = NAMES
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    for name in names:
        pads = r.pad_groups[name]
        print(f"== {name} ({len(pads)} pads)")
        basins = []
        for i, rec in enumerate(pads):
            t0 = time.time()
            seen = basin_of(r, name, rec)
            size = int(sum(s.sum() for s in seen))
            basins.append(seen)
            bn = boundary_nets(r, name, seen) if size < 20000 else []
            print(f"  pad{i} @({rec['cx']:.2f},{rec['cy']:.2f}) basin={size} cells ({time.time()-t0:.0f}s) boundary={bn}")
        if len(basins) == 2:
            ov = int(sum((basins[0][L] & basins[1][L]).sum() for L in range(NL)))
            print(f"  overlap between basins: {ov} cells")


if __name__ == "__main__":
    main()
