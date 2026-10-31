#!/usr/bin/env python3
"""Rip GP19, route GP20 (dijkstra2 engine), then route GP19 back.
Pad fields are computed per-net before any ripup (GetFootprints breaks
after Remove). Saves only if BOTH end connected."""
import pcbnew, os, sys, time, heapq
import importlib.util
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("d2", os.path.join(HERE, "dijkstra2.py"))
# reuse pieces by importing module dict without running main
import types
src = open(os.path.join(HERE, "dijkstra2.py")).read()
src = src.replace('if __name__ == "__main__":\n    main()', "")
mod = types.ModuleType("d2")
mod.__dict__["__name__"] = "d2lib"
mod.__dict__["__file__"] = os.path.join(HERE, "dijkstra2.py")
sys.argv = ["dijkstra2", "GP20"]
exec(compile(src, "dijkstra2.py", "exec"), mod.__dict__)
rt = mod.rt
PATH = mod.PATH
CELL, W, H, NL = rt.CELL, rt.W, rt.H, rt.NL


def route_with_fields(r, b, name, dist, ctr):
    nid = r.net_ids[name]
    cop = r.copper; trk = r.trk_o; edge = r.edge_block

    def tier(L, y, x):
        cid = int(cop[L][y, x])
        if cid != 0 and cid != nid:
            return None
        if edge[y, x]:
            return None
        pd = float(dist[L][y, x])
        if pd < 0.115:
            return None
        o1 = int(trk[L][0][y, x]); o2 = int(trk[L][1][y, x])
        base = 1 if (o1 == 0 or o1 == nid) and (o2 == 0 or o2 == nid) else 25
        if pd < 0.16:
            base = max(base, 40)
        return base

    def via_ok(y, x):
        if not r.via_free(y, x, nid):
            return False
        for L in range(NL):
            if float(dist[L][y, x]) < 0.31:
                return False
            if float(ctr[L][y, x]) < 0.80:
                return False
        return True

    pads = r.pad_groups[name]
    ends = [r.endpoint(name, p) for p in pads]
    start = 0
    for i, e in enumerate(ends):
        n_cells = sum(len(cs) for cs in e.values())
        n_pad = sum(len(cs) for cs in r.pad_member_layer_cells(pads[i]).values())
        if n_cells > n_pad:
            start = i
            break
    sources = set()
    for L, cs in ends[start].items():
        for (y, x) in cs:
            sources.add((L, y, x))
    targets = set()
    for i, e in enumerate(ends):
        if i == start:
            continue
        for L, cs in e.items():
            for (y, x) in cs:
                targets.add((L, y, x))
    INF = float("inf")
    dmap = {}; prev = {}; pq = []
    for c in sources:
        dmap[c] = 0
        heapq.heappush(pq, (0, c))
    goal = None
    while pq:
        d, c = heapq.heappop(pq)
        if d > dmap.get(c, INF):
            continue
        if c in targets:
            goal = c
            break
        L, y, x = c
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H):
                    continue
                w = tier(L, ny, nx)
                if w is None:
                    continue
                if dx != 0 and dy != 0:
                    if tier(L, y, nx) is None or tier(L, ny, x) is None:
                        continue
                k = (L, ny, nx)
                nd = d + w
                if nd < dmap.get(k, INF):
                    dmap[k] = nd; prev[k] = c
                    heapq.heappush(pq, (nd, k))
        for oL in range(NL):
            if oL == L:
                continue
            if not via_ok(y, x):
                continue
            k = (oL, y, x)
            nd = d + 40
            if nd < dmap.get(k, INF):
                dmap[k] = nd; prev[k] = c
                heapq.heappush(pq, (nd, k))
    if goal is None:
        return False
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path = path[::-1]
    r.commit(name, path, b.FindNet(name))
    return r.net_components(name) <= 1


def main():
    b = pcbnew.LoadBoard(PATH)
    f20 = mod.build_pad_fields(b, "GP20")
    f19 = mod.build_pad_fields(b, "GP19")
    r = rt.R(b)
    r.ingest()
    saved19 = list(r.geom["GP19"]["objects"]) if "GP19" in r.geom else []
    r.ripup("GP19")
    if "GP20" in r.geom:
        r.ripup("GP20")
    t0 = time.time()
    ok20 = route_with_fields(r, b, "GP20", *f20)
    print(f"GP20: {'OK' if ok20 else 'NO PATH'} ({time.time()-t0:.0f}s)", flush=True)
    if not ok20:
        return
    t0 = time.time()
    ok19 = route_with_fields(r, b, "GP19", *f19)
    print(f"GP19: {'OK' if ok19 else 'NO PATH'} ({time.time()-t0:.0f}s)", flush=True)
    if ok19:
        pcbnew.SaveBoard(PATH, b)
        print("SAVED both", flush=True)
    else:
        # restore GP19 original objects, keep GP20 (report state)
        if "GP19" in r.geom:
            r.ripup("GP19")
        f4restore = importlib.util.spec_from_file_location("fix4", os.path.join(HERE, "fix4.py"))
        f4 = importlib.util.module_from_spec(f4restore)
        sys.argv = ["x"]
        f4restore.loader.exec_module(f4)
        f4.restore(r, "GP19", saved19)
        pcbnew.SaveBoard(PATH, b)
        print("GP19 restored original; GP20 kept. SAVED", flush=True)


if __name__ == "__main__":
    main()
