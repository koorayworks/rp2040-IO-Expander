#!/usr/bin/env python3
"""Strict Dijkstra: track cells must satisfy router's track_free (o1+o2
@TRK_R), vias router's via_free. No relaxation anywhere.
Usage: python3 dijkstra_strict.py NET [--rip]"""
import pcbnew, os, sys, time, heapq
import importlib.util

NAME = sys.argv[1]
RIP = "--rip" in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fix1", os.path.join(HERE, "fix1.py"))
f1 = importlib.util.module_from_spec(spec)
sys.argv = ["dijkstra_strict"]
spec.loader.exec_module(f1)
rt = f1.rt
rt.OFF_TRK = rt.offsets_within(0.130)
rt.OFF_VIA = rt.offsets_within(0.270)
PATH = f1.PATH
CELL, W, H, NL = rt.CELL, rt.W, rt.H, rt.NL


def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    name = NAME
    nid = r.net_ids[name]
    if RIP and name in r.geom:
        r.ripup(name)
    if r.net_components(name) <= 1:
        print(f"{name}: already connected", flush=True)
        return
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
    t0 = time.time()
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
        print(f"{name}: NO PATH real ({time.time()-t0:.0f}s)", flush=True)
        return
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path = path[::-1]
    r.commit(name, path, b.FindNet(name))
    ok = r.net_components(name) <= 1
    print(f"{name}: {'OK' if ok else 'commit failed'} pathlen={len(path)} ({time.time()-t0:.0f}s)", flush=True)
    if ok:
        pcbnew.SaveBoard(PATH, b)


if __name__ == "__main__":
    main()
