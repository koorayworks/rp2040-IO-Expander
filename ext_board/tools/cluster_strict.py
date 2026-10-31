#!/usr/bin/env python3
"""Strict packing of the J6 cluster: rip GP19,GP20,GP21,GP22,GP23 and
re-route in the given order with the strict Dijkstra. Failed nets get
their original objects restored. Order from argv."""
import pcbnew, os, sys, time, heapq
import importlib.util

ORDER = sys.argv[1:] or ["GP21", "GP20", "GP22", "GP19", "GP23"]
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fix1", os.path.join(HERE, "fix1.py"))
f1 = importlib.util.module_from_spec(spec)
sys.argv = ["cluster_strict"]
spec.loader.exec_module(f1)
rt = f1.rt
PATH = f1.PATH
CELL, W, H, NL = rt.CELL, rt.W, rt.H, rt.NL
spec4 = importlib.util.spec_from_file_location("fix4", os.path.join(HERE, "fix4.py"))
f4 = importlib.util.module_from_spec(spec4)
sys.argv = ["cluster_strict"]
spec4.loader.exec_module(f4)


def strict_route(r, b, name):
    nid = r.net_ids[name]
    tf = r.track_free
    vf = r.via_free
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
                if not tf(L, ny, nx, nid):
                    continue
                if dx != 0 and dy != 0:
                    if not (tf(L, y, nx, nid) and tf(L, ny, x, nid)):
                        continue
                k = (L, ny, nx)
                nd = d + (14 if dx != 0 and dy != 0 else 10)
                if nd < dmap.get(k, INF):
                    dmap[k] = nd; prev[k] = c
                    heapq.heappush(pq, (nd, k))
        for oL in range(NL):
            if oL == L:
                continue
            if not vf(y, x, nid):
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
    r = rt.R(b)
    r.ingest()
    nets = ["GP19", "GP20", "GP21", "GP22", "GP23"]
    saved = {}
    for n in nets:
        if n in r.geom:
            saved[n] = list(r.geom[n]["objects"])
            r.ripup(n)
    results = {}
    for n in ORDER:
        t0 = time.time()
        ok = strict_route(r, b, n)
        print(f"{n}: {'OK' if ok else 'NO PATH'} ({time.time()-t0:.0f}s)", flush=True)
        results[n] = ok
        if not ok and n in saved:
            if n in r.geom:
                r.ripup(n)
            f4.restore(r, n, saved[n])
            print(f"{n}: restored original", flush=True)
    pcbnew.SaveBoard(PATH, b)
    print("SAVED:", results, flush=True)


if __name__ == "__main__":
    main()
