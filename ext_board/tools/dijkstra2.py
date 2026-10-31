#!/usr/bin/env python3
"""Dijkstra with real pad-ellipse clearance fields.

tier(L,y,x) for net nid:
  - foreign track/pad copper in model copper array: forbidden
  - pad edge distance (real ellipse geometry, all footprints):
      tracks: >=0.16mm -> cost 1 | 0.115..0.16 -> cost 40 | <0.115 forbidden
      (plus router STRICT track_free required for cost 1; o1-only -> >=25)
  - vias: strict via_free AND pad edge dist >= 0.31 AND (for PTH pads)
    centre distance >= 0.80.
Usage: python3 dijkstra2.py NET [--rip]
"""
import pcbnew, os, sys, time, heapq, math
import importlib.util
import numpy as np

NAME = sys.argv[1]
RIP = "--rip" in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fix4", os.path.join(HERE, "fix4.py"))
f4 = importlib.util.module_from_spec(spec)
sys.argv = ["dijkstra2"]
spec.loader.exec_module(f4)
rt = f4.rt
PATH = f4.PATH
CELL, W, H, NL = rt.CELL, rt.W, rt.H, rt.NL
LAY = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}


def build_pad_fields(b, nid_name):
    """dist[L]: float array (H,W) of approx distance (mm) from cell centre to
    nearest FOREIGN pad ellipse edge (negative inside). pth_ctr[L]: distance to
    nearest foreign PTH pad centre."""
    INF = 99.0
    dist = [np.full((H, W), INF, dtype=np.float32) for _ in range(NL)]
    ctr = [np.full((H, W), INF, dtype=np.float32) for _ in range(NL)]
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == nid_name or not p.GetNetname():
                continue
            pos = p.GetPosition()
            cx, cy = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            sz = p.GetSize()
            rx, ry = pcbnew.ToMM(sz.x) / 2.0, pcbnew.ToMM(sz.y) / 2.0
            layers = []
            for lc, li in LAY.items():
                if p.IsOnLayer(lc):
                    layers.append(li)
            if p.GetDrillSize().x > 0:
                layers = [0, 1, 2]  # through pad: all layers
            if not layers:
                continue
            R = max(rx, ry) + 0.45
            x0 = max(0, int((cx - R) / CELL)); x1 = min(W - 1, int((cx + R) / CELL))
            y0 = max(0, int((cy - R) / CELL)); y1 = min(H - 1, int((cy + R) / CELL))
            ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
            dx = (xs * CELL - cx) / max(rx, 0.05)
            dy = (ys * CELL - cy) / max(ry, 0.05)
            q = np.sqrt(dx * dx + dy * dy)
            # approx edge distance: (q-1) * min(rx,ry) (conservative-ish)
            d = (q - 1.0) * min(rx, ry)
            dc = np.sqrt((xs * CELL - cx) ** 2 + (ys * CELL - cy) ** 2)
            for li in layers:
                sub = dist[li][y0:y1 + 1, x0:x1 + 1]
                np.minimum(sub, d, out=sub)
                if p.GetDrillSize().x > 0:
                    subc = ctr[li][y0:y1 + 1, x0:x1 + 1]
                    np.minimum(subc, dc, out=subc)
    return dist, ctr


def main():
    b = pcbnew.LoadBoard(PATH)
    name = NAME
    dist, ctr = build_pad_fields(b, name)
    r = rt.R(b)
    r.ingest()
    nid = r.net_ids[name]
    if RIP and name in r.geom:
        r.ripup(name)
    if r.net_components(name) <= 1:
        print(f"{name}: already connected", flush=True)
        return
    cop = r.copper
    trk = r.trk_o
    edge = r.edge_block

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
    dmap = {}
    prev = {}
    pq = []
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
                w = tier(L, ny, nx)
                if w is None:
                    continue
                if dx != 0 and dy != 0:
                    if tier(L, y, nx) is None or tier(L, ny, x) is None:
                        continue
                k = (L, ny, nx)
                nd = d + w
                if nd < dmap.get(k, INF):
                    dmap[k] = nd
                    prev[k] = c
                    heapq.heappush(pq, (nd, k))
        for oL in range(NL):
            if oL == L:
                continue
            if not via_ok(y, x):
                continue
            k = (oL, y, x)
            nd = d + 40
            if nd < dmap.get(k, INF):
                dmap[k] = nd
                prev[k] = c
                heapq.heappush(pq, (nd, k))
    if goal is None:
        print(f"{name}: NO PATH ({time.time()-t0:.0f}s)", flush=True)
        return
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path = path[::-1]
    r.commit(name, path, b.FindNet(name))
    ok = r.net_components(name) <= 1
    print(f"{name}: {'OK' if ok else 'FAILED components'} pathlen={len(path)} ({time.time()-t0:.0f}s)", flush=True)
    if ok:
        pcbnew.SaveBoard(PATH, b)


if __name__ == "__main__":
    main()
