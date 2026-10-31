#!/usr/bin/env python3
"""Relaxed multi-source Dijkstra tree router (offsets 0.110/0.235).
Cells are (L, y, x); uses router.R track_free/via_free/commit.
Usage: relax_route.py NET [NET...]"""
import pcbnew, os, sys, time, heapq
import importlib.util
ARGS = sys.argv[1:]
HERE = "/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board/tools"
spec = importlib.util.spec_from_file_location("fix1", os.path.join(HERE, "fix1.py"))
f1 = importlib.util.module_from_spec(spec)
sys.argv = ["relax_route"]
spec.loader.exec_module(f1)
rt = f1.rt
import os as _os
_OT = float(_os.environ.get("OFF_TRK", "0.110")); _OV = float(_os.environ.get("OFF_VIA", "0.235"))
rt.OFF_TRK = rt.offsets_within(_OT)
rt.OFF_VIA = rt.offsets_within(_OV)
PATH = f1.PATH
W, H, NL = rt.W, rt.H, rt.NL
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

def route_leg(r, name, board, timeout=280):
    nid = r.net_ids[name]
    pads = r.pad_groups[name]
    ends = [r.endpoint(name, p) for p in pads]
    src = {}; dist = {}; parent = {}; pq = []
    for gi, e in enumerate(ends):
        for l, cells in e.items():
            for (y, x) in cells:
                key = (l, y, x)
                if key not in dist:
                    dist[key] = 0.0; src[key] = gi; parent[key] = None
                    heapq.heappush(pq, (0.0, l, y, x))
    tf = r.track_free; vf = r.via_free
    best = None; bestpair = None
    t0 = time.time()
    while pq:
        d, l, y, x = heapq.heappop(pq)
        if d > dist.get((l, y, x), 1e18) + 1e-9: continue
        if best is not None and d > best: break
        if time.time() - t0 > timeout: return False
        s = src[(l, y, x)]
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H): continue
            if not tf(l, ny, nx, nid): continue
            w = 1.4142 if dx and dy else 1.0
            key = (l, ny, nx)
            if key in src and src[key] != s:
                tot = d + w + dist[key]
                if best is None or tot < best: best = tot; bestpair = ((l, y, x), key)
                continue
            nd = d + w
            if nd < dist.get(key, 1e18) - 1e-9:
                dist[key] = nd; src[key] = s; parent[key] = (l, y, x)
                heapq.heappush(pq, (nd, l, ny, nx))
        if vf(y, x, nid):
            for l2 in range(NL):
                if l2 == l: continue
                key = (l2, y, x)
                if key in src and src[key] != s:
                    tot = d + 40.0 + dist[key]
                    if best is None or tot < best: best = tot; bestpair = ((l, y, x), key)
                    continue
                nd = d + 40.0
                if nd < dist.get(key, 1e18) - 1e-9:
                    dist[key] = nd; src[key] = s; parent[key] = (l, y, x)
                    heapq.heappush(pq, (nd, l2, y, x))
    if bestpair is None: return False
    def chain(k):
        pts = []
        while k is not None:
            pts.append(k); k = parent[k]
        return pts
    p1 = chain(bestpair[0]); p2 = chain(bestpair[1])
    path = list(reversed(p1)) + p2
    r.commit(name, path, board.FindNet(name))
    return True

def main():
    for name in ARGS:
        t0 = time.time(); legs = 0
        while True:
            b = pcbnew.LoadBoard(PATH)
            r = rt.R(b); r.ingest()
            if r.net_components(name) <= 1:
                print(f"{name}: connected ({legs} legs, {time.time()-t0:.0f}s)", flush=True)
                break
            ok = route_leg(r, name, b)
            if not ok:
                print(f"{name}: LEG FAIL after {legs} legs ({time.time()-t0:.0f}s)", flush=True)
                break
            pcbnew.SaveBoard(PATH, b)
            legs += 1
            if legs > 8:
                print(f"{name}: too many legs", flush=True); break

main()
