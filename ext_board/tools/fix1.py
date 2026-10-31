#!/usr/bin/env python3
"""Fast repair driver: centroid-heuristic windowed A* on the router model,
in-process repair loop with rip-up swaps. Saves after every net that gets
connected. Usage: fix1.py NET [NET ...]  (default: all known targets)"""
import pcbnew, os, sys, time, math, heapq
import importlib.util

ARGS = sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["fix1"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
CELL, W, H, NL = rt.CELL, rt.W, rt.H, rt.NL

ALL_TARGETS = ["SWDCLK", "GP21", "EX3", "GP17", "TB4", "GPIO6", "GPIO7",
               "GPIO15", "GPIO28", "GPIO29"]


def fast_astar(r, nid, sources, target_cells, th_switch, via_cost=1.8,
               max_exp=3000000, w_h=2.0, window=None):
    """target_cells: set of (L,y,x). Heuristic: distance to target centroid."""
    if not target_cells:
        return None
    tys = [c[1] for c in target_cells]; txs = [c[2] for c in target_cells]
    cy = sum(tys) / len(tys); cx = sum(txs) / len(txs)
    tgt = target_cells
    INF = float("inf")
    g = {}; parent = {}; pq = []
    for L, cells in sources.items():
        cells = list(cells)
        push = cells[::3] if len(cells) > 24 else cells
        for (y, x) in push:
            k = (L, y, x)
            if k in g:
                continue
            g[k] = 0.0
            heapq.heappush(pq, (math.hypot(cy - y, cx - x) * w_h, 0.0, k))
    exp = 0
    tf = r.track_free
    while pq:
        f, gc, k = heapq.heappop(pq)
        if gc > g.get(k, INF):
            continue
        if k in tgt:
            path = [k]
            while path[-1] in parent:
                path.append(parent[path[-1]])
            return path[::-1]
        exp += 1
        if exp > max_exp:
            return None
        L, y, x = k
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < W and 0 <= ny_ < H):
                    continue
                if window and not (window[0] <= nx_ <= window[1] and window[2] <= ny_ <= window[3]):
                    continue
                if not tf(L, ny_, nx_, nid):
                    continue
                if dx != 0 and dy != 0:
                    if not (tf(L, y, nx_, nid) and tf(L, ny_, x, nid)):
                        continue
                    step = 1.41421
                else:
                    step = 1.0
                nk = (L, ny_, nx_); ng = gc + step
                if ng < g.get(nk, INF):
                    g[nk] = ng; parent[nk] = k
                    heapq.heappush(pq, (ng + math.hypot(cy - ny_, cx - nx_) * w_h, ng, nk))
        for oL in range(NL):
            if oL == L:
                continue
            if (y, x) in th_switch:
                ng = gc + 0.8
            elif r.via_free(y, x, nid):
                ng = gc + via_cost
            else:
                continue
            if window and not (window[0] <= x <= window[1] and window[2] <= y <= window[3]):
                continue
            nk = (oL, y, x)
            if ng < g.get(nk, INF):
                g[nk] = ng; parent[nk] = k
                heapq.heappush(pq, (ng + math.hypot(cy - y, cx - x) * w_h, ng, nk))
    return None


def route_fast(r, name, via_cost=1.8, w_h=2.0, margin=25.0):
    pads = r.pad_groups[name]
    if len(pads) == 1:
        return True
    net_obj = r.b.FindNet(name)
    th = r.th_cells.get(name, set())
    ends = [r.endpoint(name, p) for p in pads]
    start = 0
    for i, e in enumerate(ends):
        n_cells = sum(len(cs) for cs in e.values())
        n_pad = sum(len(cs) for cs in r.pad_member_layer_cells(pads[i]).values())
        if n_cells > n_pad:
            start = i
            break
    cur = {L: set(cs) for L, cs in ends[start].items()}
    tree_pts = [(pads[start]["cx"], pads[start]["cy"])]
    remaining = [i for i in range(len(pads)) if i != start]
    # window from all pads + margin
    xs = [p["cx"] for p in pads]; ys = [p["cy"] for p in pads]
    window = (max(0, int((min(xs) - margin) / CELL)), min(W - 1, int((max(xs) + margin) / CELL)),
              max(0, int((min(ys) - margin) / CELL)), min(H - 1, int((max(ys) + margin) / CELL)))
    ok = True
    while remaining:
        def dist(i):
            return min(math.hypot(pads[i]["cx"] - tx, pads[i]["cy"] - ty) for (tx, ty) in tree_pts)
        nxt = min(remaining, key=dist)
        tgt = set()
        for L, cells in ends[nxt].items():
            for (y, x) in cells:
                tgt.add((L, y, x))
        path = fast_astar(r, r.net_ids[name], cur, tgt, th, via_cost=via_cost, w_h=w_h, window=window)
        if path is None:
            ok = False
            remaining.remove(nxt)
            continue
        r.commit(name, path, net_obj)
        for L, cells in ends[nxt].items():
            cur.setdefault(L, set()).update(cells)
        for (L, y, x) in path:
            cur.setdefault(L, set()).add((y, x))
        tree_pts.append((pads[nxt]["cx"], pads[nxt]["cy"]))
        remaining.remove(nxt)
    return ok


def try_net(r, name, unrouted):
    """Try plain, then rip-up swaps. Returns True if name connected at end."""
    if r.net_components(name) <= 1:
        return True
    if route_fast(r, name) and r.net_components(name) <= 1:
        return True
    if name in r.geom:
        r.ripup(name)
    blockers = rt.corridor_blockers(r, name, set())
    for blk in blockers[:4]:
        if blk not in r.geom:
            continue
        r.ripup(blk)
        if route_fast(r, name) and r.net_components(name) <= 1:
            if route_fast(r, blk) and r.net_components(blk) <= 1:
                print(f"    swap {blk}: both connected", flush=True)
            else:
                if blk in r.geom:
                    r.ripup(blk)
                print(f"    swap {blk}: {name} won, {blk} queued", flush=True)
                unrouted.add(blk)
            return True
        else:
            if name in r.geom:
                r.ripup(name)
            route_fast(r, blk)  # restore (best effort)
    return False


def main():
    targets = ARGS or ALL_TARGETS
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    unrouted = set()
    for n in list(r.pad_groups):
        if n != "GND" and r.net_components(n) > 1:
            unrouted.add(n)
    print("model-unrouted at start:", sorted(unrouted), flush=True)
    t0 = time.time()
    for rnd in range(3):
        todo = [n for n in targets if n in unrouted]
        if not todo:
            break
        progress = False
        for name in todo:
            ts = time.time()
            got = try_net(r, name, unrouted)
            if got and r.net_components(name) <= 1:
                unrouted.discard(name)
                pcbnew.SaveBoard(PATH, b)
                progress = True
                print(f"[{rnd}] {name}: OK ({time.time()-ts:.0f}s) left={sorted(unrouted & set(targets))}", flush=True)
            else:
                print(f"[{rnd}] {name}: FAIL ({time.time()-ts:.0f}s)", flush=True)
        if not progress:
            break
    print("FINAL model-unrouted (targets):", sorted(unrouted & set(targets)), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
