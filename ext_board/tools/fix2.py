#!/usr/bin/env python3
"""Fast A* router on router.py's model (set-based neighbors), with rip-up swaps.

Usage: python3 fix2.py NET [NET...]
Fast neighbor generation: precomputed blocked index sets per layer; no numpy
in the hot loop. Falls back to rip-up of corridor blockers like fix1.
"""
import sys, os, time, heapq, math
ARGS = sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
import router as rt

PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
ALL_TARGETS = ["GPIO6", "GPIO7", "GPIO15", "GPIO28", "GPIO29",
               "GP21", "SWDCLK", "GP17", "EX3", "TB4"]


class Fast:
    def __init__(self, r):
        self.r = r
        self.W, self.H = r.W, r.H
        # blocked[L]: set of y*W+x where grid==1 (all nets stamped)
        self.blocked = []
        for L in range(3):
            ys, xs = (r.grid[L] == 1).nonzero()
            self.blocked.append(set((ys * self.W + xs).tolist()))
        # via-forbidden (x,y): via_stamp or any-layer blocked
        vb = (r.via_stamp == 1)
        anyb = (r.grid[0] == 1) | (r.grid[1] == 1) | (r.grid[2] == 1)
        m = vb | anyb
        ys, xs = m.nonzero()
        self.via_bad = set((ys * self.W + xs).tolist())

    def own_cells(self, name):
        r = self.r
        cells = set()
        for (cx, cy, L) in r.pads_of(name):
            cells.add((L, cy * self.W + cx))
        for (cx, cy, L) in r.geom.get(name, []):
            cells.add((L, cy * self.W + cx))
        return cells

    def astar(self, name, via_cost=1.8, max_exp=2_500_000):
        r = self.r
        W, H = self.W, self.H
        own = self.own_cells(name)
        blocked = []
        for L in range(3):
            b = self.blocked[L] - {i for (l, i) in own if l == L}
            blocked.append(b)
        via_bad = self.via_bad - {i for (l, i) in own}
        groups = r.pad_groups[name]
        starts = set()
        tset = set()
        for gi, cells in enumerate(groups):
            tgt = cells if gi == 0 else None
            for (cx, cy, L) in cells:
                if gi == 0:
                    tset.add((L, cy * W + cx))
                else:
                    starts.add((L, cy * W + cx))
        for (L, i) in own:
            starts.add((L, i))
        starts -= tset
        if not starts or not tset:
            return None
        txs = [i % W for (l, i) in tset]
        tys = [i // W for (l, i) in tset]
        tcx = sum(txs) / len(txs); tcy = sum(tys) / len(tys)
        INF = float("inf")
        g = {}
        came = {}
        pq = []
        for (L, i) in starts:
            g[(L, i)] = 0.0
            x, y = i % W, i // W
            h = math.hypot(x - tcx, y - tcy)
            heapq.heappush(pq, (2.0 * h, 0.0, L, i))
        exp = 0
        DIRS = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142))
        while pq:
            f, gv, L, i = heapq.heappop(pq)
            if gv > g.get((L, i), INF):
                continue
            if (L, i) in tset:
                path = [(i % W, i // W, L)]
                cur = (L, i)
                while cur in came:
                    cur = came[cur]
                    path.append((cur[1] % W, cur[1] // W, cur[0]))
                return path[::-1]
            exp += 1
            if exp > max_exp:
                return None
            x, y = i % W, i // W
            bL = blocked[L]
            for dx, dy, c in DIRS:
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= W or ny >= H:
                    continue
                ni = ny * W + nx
                if ni in bL and (L, ni) not in tset and (L, ni) not in starts:
                    continue
                ng = gv + c
                if ng < g.get((L, ni), INF):
                    g[(L, ni)] = ng
                    came[(L, ni)] = (L, i)
                    h = math.hypot(nx - tcx, ny - tcy)
                    heapq.heappush(pq, (ng + 2.0 * h, ng, L, ni))
            if i not in via_bad:
                for L2 in (0, 1, 2):
                    if L2 == L:
                        continue
                    if i in blocked[L2] and (L2, i) not in tset and (L2, i) not in starts:
                        continue
                    ng = gv + via_cost
                    if ng < g.get((L2, i), INF):
                        g[(L2, i)] = ng
                        came[(L2, i)] = (L, i)
                        h = math.hypot(x - tcx, y - tcy)
                        heapq.heappush(pq, (ng + 2.0 * h, ng, L2, i))
        return None

    def route(self, name):
        if self.r.net_components(name) <= 1:
            return True
        path = self.astar(name)
        if not path:
            return False
        self.r.commit_path(name, path)
        return self.r.net_components(name) <= 1

    def try_net(self, name, unrouted):
        r = self.r
        if self.route(name):
            return True
        if name in r.geom:
            r.ripup(name)
        blockers = rt.corridor_blockers(r, name, set())
        for blk in blockers[:4]:
            if blk in unrouted or blk == "GND":
                continue
            saved = list(r.geom.get(blk, []))
            r.ripup(blk)
            self.__init__(r)  # refresh after ripup
            if self.route(name):
                self.__init__(r)  # refresh with name's new tracks stamped
                if self.route(blk):
                    print(f"    swap {blk}: re-routed OK", flush=True)
                    return True
                print(f"    swap {blk}: re-route FAILED, restoring both", flush=True)
                r.ripup(blk)   # drop partial blk route
                r.ripup(name)  # give up name's route to keep board consistent
                _restore(r, blk, saved)
                self.__init__(r)
            else:
                _restore(r, blk, saved)
                self.__init__(r)
        return self.r.net_components(name) <= 1


def _restore(r, name, cells):
    """Rebuild a net's geometry from a saved cell list (as zero-len-free path)."""
    # cells are (cx, cy, L) unordered; rebuild via commit on sorted runs:
    # simplest: group by layer, sort, and connect consecutive cells with tracks
    from collections import defaultdict
    by = defaultdict(list)
    for (cx, cy, L) in cells:
        by[L].append((cx, cy))
    # Use A* target = pads: instead re-route with the plain fast router is not
    # available here; fall back: mark cells conductive through geom injection
    # is complex -- caller should avoid this path. We rebuild straight segments
    # between same-layer adjacent (8-neighbour) cells.
    segs = []
    cellset = set(cells)
    for (cx, cy, L) in cells:
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            if (cx + dx, cy + dy, L) in cellset:
                segs.append(((cx, cy, L), (cx + dx, cy + dy, L)))
    b = r.b
    net = b.FindNet(name)
    for (a, bcell) in segs:
        t = pcbnew.PCB_TRACK(b)
        t.SetNet(net)
        t.SetLayer(a[2])
        t.SetWidth(pcbnew.FromMM(rt.TRACK_W))
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0] * rt.GRID),
                                   pcbnew.FromMM(a[1] * rt.GRID)))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(bcell[0] * rt.GRID),
                                 pcbnew.FromMM(bcell[1] * rt.GRID)))
        b.Add(t)
    r.ingest()


def main():
    targets = ARGS or ALL_TARGETS
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    F = Fast(r)
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
            got = F.try_net(name, unrouted)
            if got and r.net_components(name) <= 1:
                unrouted.discard(name)
                pcbnew.SaveBoard(PATH, b)
                F = Fast(r)
                progress = True
                print(f"[{rnd}] {name}: OK ({time.time()-ts:.0f}s) left={sorted(unrouted & set(targets))}", flush=True)
            else:
                print(f"[{rnd}] {name}: FAIL ({time.time()-ts:.0f}s)", flush=True)
        if not progress:
            break
    print("FINAL model-unrouted (targets):", sorted(unrouted & set(targets)), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
