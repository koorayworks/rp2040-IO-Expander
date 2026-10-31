#!/usr/bin/env python3
"""Dijkstra router on the router.py model.

Cost tiers per cell (same layer move):
  free under STRICT track_free (o1+o2 dilation) : 1
  free under relaxed track_free (o1 only)      : 25
  blocked by dilation only (no foreign copper) : 80
  foreign copper cell                          : forbidden
Via move: only where router's strict via_free holds, cost 40.
Diagonal moves require both orthogonal neighbours to be non-copper.

Usage: python3 dijkstra_route.py NET [NET...]  (routes in given order,
saves after each success; nets are NOT ripped automatically except
--rip-first flag per whole run)
"""
import pcbnew, os, sys, time, heapq
import importlib.util

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
RIP = "--rip" in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fix4", os.path.join(HERE, "fix4.py"))
f4 = importlib.util.module_from_spec(spec)
sys.argv = ["dijkstra_route"]
spec.loader.exec_module(f4)
rt = f4.rt
PATH = f4.PATH
CELL, W, H, NL = rt.CELL, rt.W, rt.H, rt.NL


def dijkstra_path(r, name):
    nid = r.net_ids[name]
    cop = r.copper
    trk = r.trk_o
    edge = r.edge_block

    def tier(L, y, x):
        cid = int(cop[L][y, x])
        if cid != 0 and cid != nid:
            return None
        if edge[y, x]:
            return None
        o1 = int(trk[L][0][y, x]); o2 = int(trk[L][1][y, x])
        if o1 == 0 or o1 == nid:
            if o2 == 0 or o2 == nid:
                return 1
            return 25
        return 80

    pads = r.pad_groups[name]
    if len(pads) < 2:
        return None
    # sources: pad group 0 + touching geometry (endpoint), targets: rest pads
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
    dist = {}
    prev = {}
    pq = []
    for c in sources:
        dist[c] = 0
        heapq.heappush(pq, (0, c))
    goal = None
    while pq:
        d, c = heapq.heappop(pq)
        if d > dist.get(c, INF):
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
                if nd < dist.get(k, INF):
                    dist[k] = nd
                    prev[k] = c
                    heapq.heappush(pq, (nd, k))
        for oL in range(NL):
            if oL == L:
                continue
            if not r.via_free(y, x, nid):
                continue
            k = (oL, y, x)
            nd = d + 40
            if nd < dist.get(k, INF):
                dist[k] = nd
                prev[k] = c
                heapq.heappush(pq, (nd, k))
    if goal is None:
        return None
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    return path[::-1]


def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    # NOTE: no relaxed patch: tier() reads trk_o directly; track_free unused.
    for name in ARGS:
        if RIP and name in r.geom:
            r.ripup(name)
        if r.net_components(name) <= 1:
            print(f"{name}: already connected", flush=True)
            continue
        t0 = time.time()
        path = dijkstra_path(r, name)
        if not path:
            print(f"{name}: NO PATH ({time.time()-t0:.0f}s)", flush=True)
            continue
        n80 = 0
        r.commit(name, path, b.FindNet(name))
        ok = r.net_components(name) <= 1
        print(f"{name}: {'OK' if ok else 'commit but components>1'} pathlen={len(path)} ({time.time()-t0:.0f}s)", flush=True)
        if ok:
            pcbnew.SaveBoard(PATH, b)


if __name__ == "__main__":
    main()
