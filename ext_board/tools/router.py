#!/usr/bin/env python3
"""Self-contained grid router (rebuild of the route2/3/4/6 stack).
0.05mm grid, 3 signal layers (F.Cu=0, In2.Cu=1, B.Cu=2), through vias,
0.10mm track / 0.10mm clearance model, via 0.40/0.20.
Ingests existing tracks as per-net geometry, routes the remaining nets,
with rip-up repair swaps. Saves after every success."""
import pcbnew, os, math, heapq, time, sys
import numpy as np

MM = pcbnew.FromMM
CELL = 0.05
W, H = 361, 871
TRK_R = 0.155
VIA_R = 0.305
OBST = -1
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
NL = 3

def cell_of(v):
    return int(round(v / CELL))

def offsets_within(r_mm):
    r = r_mm / CELL
    out = []
    n = int(math.ceil(r))
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            if math.hypot(dx, dy) <= r + 1e-9:
                out.append((dx, dy))
    return out

OFF_TRK = offsets_within(TRK_R)
OFF_VIA = offsets_within(VIA_R)

def shift(arr, dx, dy):
    out = np.zeros_like(arr)
    xs = slice(max(0, dx), min(arr.shape[1], arr.shape[1] + dx))
    xt = slice(max(0, -dx), min(arr.shape[1], arr.shape[1] - dx))
    ys = slice(max(0, dy), min(arr.shape[0], arr.shape[0] + dy))
    yt = slice(max(0, -dy), min(arr.shape[0], arr.shape[0] - dy))
    out[ys, xs] = arr[yt, xt]
    return out

def dilate2(copper, offsets):
    o1 = np.zeros_like(copper)
    o2 = np.zeros_like(copper)
    for dx, dy in offsets:
        sh = shift(copper, dx, dy)
        new1 = (o1 == 0) & (sh != 0)
        o1 = np.where(new1, sh, o1)
        new2 = (o2 == 0) & (sh != 0) & (sh != o1)
        o2 = np.where(new2, sh, o2)
    return o1, o2

class R:
    def __init__(self, board):
        self.b = board
        self.copper = [np.zeros((H, W), dtype=np.int32) for _ in range(NL)]
        self.edge_block = np.zeros((H, W), dtype=bool)
        self.net_ids = {}
        self.pad_groups = {}
        self.th_cells = {}
        self.geom = {}
        self._stamp_edges()
        self._collect_pads()
        self.pads_copper = [c.copy() for c in self.copper]
        self.rebuild_blockers()

    def nid(self, name):
        if name not in self.net_ids:
            self.net_ids[name] = len(self.net_ids) + 1
        return self.net_ids[name]

    def _stamp_edges(self):
        c = self.edge_block
        m = int(round(0.2 / CELL))
        c[:, :m] = True
        c[:, W - m:] = True
        c[:m, :] = True
        c[H - m:, :] = True
        kx0, kx1 = int(3.0 / CELL), int(15.0 / CELL)
        ky0 = int(38.0 / CELL)
        c[ky0:, kx0:kx1] = True
        # USB-C NPTH holes at (6.11,2.17) and (11.89,2.17): keep radius 0.8mm
        for (hx, hy) in [(122, 43), (238, 43)]:
            rr = int(round(0.8 / CELL))
            for dy in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    if math.hypot(dx, dy) <= rr:
                        yy, xx = hy + dy, hx + dx
                        if 0 <= yy < H and 0 <= xx < W:
                            c[yy, xx] = True
        for (hx, hy) in [(36, 824), (324, 824)]:
            rr = int(round(1.35 / CELL))
            for dy in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    if math.hypot(dx, dy) <= rr:
                        yy, xx = hy + dy, hx + dx
                        if 0 <= yy < H and 0 <= xx < W:
                            c[yy, xx] = True

    def _pad_cells(self, rec):
        ix0 = max(0, int(math.ceil(rec["x0"] / CELL - 1e-6)))
        ix1 = min(W - 1, int(math.floor(rec["x1"] / CELL + 1e-6)))
        iy0 = max(0, int(math.ceil(rec["y0"] / CELL - 1e-6)))
        iy1 = min(H - 1, int(math.floor(rec["y1"] / CELL + 1e-6)))
        cells = [(y, x) for y in range(iy0, iy1 + 1) for x in range(ix0, ix1 + 1)]
        cc = (cell_of(rec["cy"]), cell_of(rec["cx"]))
        if cc not in cells:
            cells.append(cc)
        return cells

    def _collect_pads(self):
        b = self.b
        for fp in b.GetFootprints():
            for pad in fp.Pads():
                name = pad.GetNetname()
                bb = pad.GetBoundingBox()
                rec = dict(name=name,
                           x0=pcbnew.ToMM(bb.GetLeft()), x1=pcbnew.ToMM(bb.GetRight()),
                           y0=pcbnew.ToMM(bb.GetTop()), y1=pcbnew.ToMM(bb.GetBottom()),
                           cx=pcbnew.ToMM(pad.GetPosition().x), cy=pcbnew.ToMM(pad.GetPosition().y),
                           layers=set(), th=pad.GetDrillSize().x > 0)
                ls = pad.GetLayerSet()
                if rec["th"]:
                    rec["layers"] = {0, 1, 2}
                else:
                    if ls.Contains(pcbnew.F_Cu):
                        rec["layers"].add(0)
                    if ls.Contains(pcbnew.B_Cu):
                        rec["layers"].add(2)
                cells = self._pad_cells(rec)
                if not name:
                    for L in range(NL):
                        for (y, x) in cells:
                            self.copper[L][y, x] = OBST
                    continue
                nid = self.nid(name)
                self.pad_groups.setdefault(name, []).append(rec)
                for L in rec["layers"]:
                    for (y, x) in cells:
                        self.copper[L][y, x] = nid
                if rec["th"]:
                    self.th_cells.setdefault(name, set()).update(cells)

    def rebuild_blockers(self):
        self.trk_o = [dilate2(self.copper[L], OFF_TRK) for L in range(NL)]
        self.via_o = [dilate2(self.copper[L], OFF_VIA) for L in range(NL)]

    def rebuild_copper(self):
        self.copper = [c.copy() for c in self.pads_copper]
        for name, g in self.geom.items():
            nid = self.net_ids[name]
            for (L, y, x) in g["cells"]:
                self.copper[L][y, x] = nid
        self.rebuild_blockers()

    def track_free(self, L, y, x, nid):
        if self.copper[L][y, x] == nid:
            return True
        if self.edge_block[y, x]:
            return False
        o1, o2 = self.trk_o[L]
        a = o1[y, x]; bq = o2[y, x]
        return (a == 0 or a == nid) and (bq == 0 or bq == nid)

    def via_free(self, y, x, nid):
        if self.edge_block[y, x]:
            return False
        for L in range(NL):
            if self.copper[L][y, x] != 0:
                return False
            o1, o2 = self.via_o[L]
            a = o1[y, x]; bq = o2[y, x]
            if not ((a == 0 or a == nid) and (bq == 0 or bq == nid)):
                return False
        return True

    def _stamp_track(self, L, a, c, nid):
        out = set()
        steps = max(2, int(math.hypot(c[0] - a[0], c[1] - a[1]) / 0.05) + 1)
        for i in range(steps + 1):
            t = i / steps
            px = a[0] + (c[0] - a[0]) * t
            py = a[1] + (c[1] - a[1]) * t
            cx, cy = cell_of(px), cell_of(py)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    xx, yy = cx + dx, cy + dy
                    if 0 <= xx < W and 0 <= yy < H:
                        if math.hypot(xx * CELL - px, yy * CELL - py) <= 0.08:
                            self.copper[L][yy, xx] = nid
                            out.add((L, yy, xx))
        return out

    def _stamp_via(self, vx, vy, nid):
        out = set()
        for L in range(NL):
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    if math.hypot(dx, dy) <= 4.5:
                        xx, yy = cell_of(vx) + dx, cell_of(vy) + dy
                        if 0 <= xx < W and 0 <= yy < H:
                            self.copper[L][yy, xx] = nid
                            out.add((L, yy, xx))
        return out

    def ripup(self, name):
        g = self.geom.pop(name, None)
        if g:
            for o in g["objects"]:
                self.b.Remove(o)
        self.rebuild_copper()

    # ---- endpoint logic (route4) ----
    def member_cells(self, rec, shrink=0.06):
        ix0 = max(0, int(math.ceil((rec["x0"] + shrink) / CELL - 1e-6)))
        ix1 = min(W - 1, int(math.floor((rec["x1"] - shrink) / CELL + 1e-6)))
        iy0 = max(0, int(math.ceil((rec["y0"] + shrink) / CELL - 1e-6)))
        iy1 = min(H - 1, int(math.floor((rec["y1"] - shrink) / CELL + 1e-6)))
        cells = [(y, x) for y in range(iy0, iy1 + 1) for x in range(ix0, ix1 + 1)]
        cc = (cell_of(rec["cy"]), cell_of(rec["cx"]))
        if not cells:
            cells = [cc]
        return cells

    def pad_member_layer_cells(self, rec):
        cells = self.member_cells(rec)
        return {L: set(cells) for L in rec["layers"]}

    def geom_components(self, name):
        cells = set(self.geom.get(name, {}).get("cells", set()))
        comps = []
        while cells:
            seed = cells.pop()
            comp = {seed}
            stack = [seed]
            while stack:
                (L, y, x) = stack.pop()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nb = (L, y + dy, x + dx)
                        if nb in cells:
                            cells.remove(nb)
                            comp.add(nb)
                            stack.append(nb)
                for oL in range(NL):
                    if oL == L:
                        continue
                    nb = (oL, y, x)
                    if nb in cells:
                        cells.remove(nb)
                        comp.add(nb)
                        stack.append(nb)
            comps.append(comp)
        return comps

    def endpoint(self, name, rec):
        base = self.pad_member_layer_cells(rec)
        out = {L: set(cs) for L, cs in base.items()}
        if name in self.geom:
            halo = set()
            for L in rec["layers"]:
                for (y, x) in self._pad_cells(rec):
                    halo.add((L, y, x))
            for comp in self.geom_components(name):
                touch = False
                for (L, y, x) in comp:
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if (L, y + dy, x + dx) in halo:
                                touch = True
                                break
                        if touch:
                            break
                    if touch:
                        break
                if touch:
                    for (L, y, x) in comp:
                        out.setdefault(L, set()).add((y, x))
        return out

    def net_components(self, name):
        """Components over pad member cells + geometry (connectivity check)."""
        cells = set()
        pad_owner = []
        for rec in self.pad_groups[name]:
            mine = set()
            for L, cs in self.pad_member_layer_cells(rec).items():
                for (y, x) in cs:
                    mine.add((L, y, x))
            pad_owner.append(mine)
            cells |= mine
        cells |= set(self.geom.get(name, {}).get("cells", set()))
        comp_id = {}
        ncomp = 0
        rest = set(cells)
        while rest:
            seed = rest.pop()
            comp = {seed}
            stack = [seed]
            while stack:
                (L, y, x) = stack.pop()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nb = (L, y + dy, x + dx)
                        if nb in rest:
                            rest.remove(nb)
                            comp.add(nb)
                            stack.append(nb)
                for oL in range(NL):
                    if oL == L:
                        continue
                    nb = (oL, y, x)
                    if nb in rest:
                        rest.remove(nb)
                        comp.add(nb)
                        stack.append(nb)
            for c in comp:
                comp_id[c] = ncomp
            ncomp += 1
        owners = set()
        for mine in pad_owner:
            for c in mine:
                if c in comp_id:
                    owners.add(comp_id[c])
                    break
        return len(owners)

    # ---- A* (route6, multi-layer, sampled heuristic) ----
    def _push(self, pq, g, parent, k, nk, ng, cy, cx, w_h):
        if ng < g.get(nk, float("inf")):
            g[nk] = ng
            parent[nk] = k
            h = float(np.min(np.hypot(cy - nk[1], cx - nk[2]))) * w_h
            heapq.heappush(pq, (ng + h, ng, nk))

    def astar_fast(self, nid, sources, target_pads, th_switch, via_cost=6.0,
                   max_exp=400000, w_h=1.5, tgt_extra=None):
        tgt = set()
        for tp in target_pads:
            for L, cells in tp.items():
                for (y, x) in cells:
                    tgt.add((L, y, x))
        if tgt_extra:
            tgt |= tgt_extra
        if not tgt:
            return None
        _pts = [(y, x) for (L, y, x) in list(tgt)]
        if len(_pts) > 240:
            _pts = _pts[:: len(_pts) // 240 + 1]
        centers = _pts
        carr = np.array(centers, dtype=np.float32)
        cy = carr[:, 0]; cx = carr[:, 1]
        INF = float("inf")
        g = {}
        parent = {}
        pq = []
        for L, cells in sources.items():
            cells = list(cells)
            push = cells[::3] if len(cells) > 24 else cells
            for (y, x) in push:
                k = (L, y, x)
                if k in g:
                    continue
                g[k] = 0.0
                h = float(np.min(np.hypot(cy - y, cx - x))) * w_h
                heapq.heappush(pq, (h, 0.0, k))
        exp = 0
        tf = self.track_free
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
                    if not tf(L, ny_, nx_, nid):
                        continue
                    if dx != 0 and dy != 0:
                        if not (tf(L, y, nx_, nid) and tf(L, ny_, x, nid)):
                            continue
                        step = 1.41421
                    else:
                        step = 1.0
                    self._push(pq, g, parent, k, (L, ny_, nx_), gc + step, cy, cx, w_h)
            for oL in range(NL):
                if oL == L:
                    continue
                if (y, x) in th_switch:
                    self._push(pq, g, parent, k, (oL, y, x), gc + 0.8, cy, cx, w_h)
                elif self.via_free(y, x, nid):
                    self._push(pq, g, parent, k, (oL, y, x), gc + via_cost, cy, cx, w_h)
        return None

    def commit(self, name, path, net_obj):
        b = self.b
        nid = self.net_ids[name]
        th = self.th_cells.get(name, set())
        real_vias = []
        for j in range(1, len(path)):
            if path[j][0] != path[j - 1][0]:
                (L, y, x) = path[j]
                if (y, x) not in th:
                    real_vias.append((x * CELL, y * CELL))
        def simplify(run):
            if len(run) <= 2:
                return run
            out = [run[0]]
            for j in range(1, len(run) - 1):
                d1 = (run[j][2] - run[j - 1][2], run[j][1] - run[j - 1][1])
                d2 = (run[j + 1][2] - run[j][2], run[j + 1][1] - run[j][1])
                if d1 != d2:
                    out.append(run[j])
            out.append(run[-1])
            return out
        runs = []
        cur = [path[0]]
        for j in range(1, len(path)):
            if path[j][0] != path[j - 1][0]:
                runs.append(cur)
                cur = [path[j]]
            else:
                cur.append(path[j])
        runs.append(cur)
        objs = []
        cells = set()
        for run in runs:
            L = run[0][0]
            srun = simplify(run)
            for a, c in zip(srun, srun[1:]):
                ax, ay = a[2] * CELL, a[1] * CELL
                cx, cy = c[2] * CELL, c[1] * CELL
                if (ax, ay) == (cx, cy):
                    continue
                t = pcbnew.PCB_TRACK(b)
                t.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
                t.SetEnd(pcbnew.VECTOR2I(MM(cx), MM(cy)))
                t.SetWidth(MM(0.10))
                t.SetLayer(LAYERS[L])
                t.SetNet(net_obj)
                b.Add(t)
                objs.append(t)
                cells |= self._stamp_track(L, (ax, ay), (cx, cy), nid)
        for (vx, vy) in real_vias:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy)))
            v.SetWidth(MM(0.40))
            v.SetDrill(MM(0.20))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(net_obj)
            b.Add(v)
            objs.append(v)
            cells |= self._stamp_via(vx, vy, nid)
        g = self.geom.setdefault(name, {"objects": [], "cells": set()})
        g["objects"].extend(objs)
        g["cells"] |= cells
        self.rebuild_blockers()

    def route_net(self, name, via_cost=6.0, max_exp=400000):
        pads = self.pad_groups[name]
        net_obj = self.b.FindNet(name)
        th = self.th_cells.get(name, set())
        if len(pads) == 1:
            return True
        ends = [self.endpoint(name, p) for p in pads]
        start = 0
        for i, e in enumerate(ends):
            n_cells = sum(len(cs) for cs in e.values())
            n_pad = sum(len(cs) for cs in self.pad_member_layer_cells(pads[i]).values())
            if n_cells > n_pad:
                start = i
                break
        cur = {L: set(cs) for L, cs in ends[start].items()}
        tree_pts = [(pads[start]["cx"], pads[start]["cy"])]
        remaining = [i for i in range(len(pads)) if i != start]
        ok = True
        while remaining:
            def dist(i):
                return min(math.hypot(pads[i]["cx"] - tx, pads[i]["cy"] - ty) for (tx, ty) in tree_pts)
            nxt = min(remaining, key=dist)
            tgt = ends[nxt]
            path = self.astar_fast(self.net_ids[name], cur, [tgt], th,
                                   via_cost=via_cost, max_exp=max_exp)
            if path is None:
                ok = False
                remaining.remove(nxt)
                continue
            self.commit(name, path, net_obj)
            for L, cells in tgt.items():
                cur.setdefault(L, set()).update(cells)
            for (L, y, x) in path:
                cur.setdefault(L, set()).add((y, x))
            tree_pts.append((pads[nxt]["cx"], pads[nxt]["cy"]))
            remaining.remove(nxt)
        return ok

    def ingest(self):
        for t in self.b.GetTracks():
            name = t.GetNetname()
            if not name:
                continue
            nid = self.nid(name)
            g = self.geom.setdefault(name, {"objects": [], "cells": set()})
            g["objects"].append(t)
            if t.GetClass() == "PCB_VIA":
                pos = t.GetPosition()
                g["cells"] |= self._stamp_via(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), nid)
            else:
                L = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}.get(t.GetLayer())
                if L is None:
                    continue
                a = (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y))
                c = (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
                g["cells"] |= self._stamp_track(L, a, c, nid)
        self.rebuild_blockers()

def span_of(r, n):
    ps = r.pad_groups[n]
    if len(ps) < 2:
        return 0.0
    xs = [p["cx"] for p in ps]; ys = [p["cy"] for p in ps]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))

NEVER_RIP = {"3V3", "USB_VBUS", "VSYS", "GND"}

def corridor_blockers(r, name, skip):
    skip = set(skip) | NEVER_RIP
    ps = r.pad_groups[name]
    xs = [p["cx"] for p in ps]; ys = [p["cy"] for p in ps]
    x0, x1 = min(xs) - 1.2, max(xs) + 1.2
    y0, y1 = min(ys) - 1.2, max(ys) + 1.2
    out = []
    for other, g in r.geom.items():
        if other == name or other in skip:
            continue
        for (L, yy, xx) in g["cells"]:
            if x0 <= xx * CELL <= x1 and y0 <= yy * CELL <= y1:
                out.append((len(g["cells"]), other))
                break
    out.sort()
    return [o for _, o in out]

def main():
    path = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
    b = pcbnew.LoadBoard(path)
    r = R(b)
    r.ingest()
    t0 = time.time()
    names = [n for n in r.pad_groups if n != "GND"]
    unrouted = set()
    for n in names:
        if r.net_components(n) > 1:
            unrouted.add(n)
    print(f"start: {len(names)} nets, unrouted={sorted(unrouted)} ({time.time()-t0:.0f}s)", flush=True)
    if os.environ.get("QUICK_ROUNDS"):
        print("skipping first pass (QUICK_ROUNDS)", flush=True)
        first_pass = []
    else:
        first_pass = sorted(unrouted, key=lambda n: span_of(r, n))
    for name in first_pass:
        if r.route_net(name, via_cost=2.5, max_exp=800000):
            if r.net_components(name) <= 1:
                unrouted.discard(name)
                pcbnew.SaveBoard(path, b)
                print(f"ROUTE {name}: OK ({time.time()-t0:.0f}s) left={len(unrouted)}", flush=True)
                continue
        print(f"ROUTE {name}: FAIL ({time.time()-t0:.0f}s)", flush=True)
    for rnd in range(5):
        if not unrouted:
            break
        progress = False
        for name in sorted(unrouted, key=lambda n: span_of(r, n)):
            print(f"TRY r{rnd} {name} ({time.time()-t0:.0f}s)", flush=True)
            if r.net_components(name) <= 1:
                unrouted.discard(name)
                progress = True
                continue
            blockers = corridor_blockers(r, name, unrouted)
            done = False
            for blk in blockers[:2]:
                r.ripup(blk)
                if r.route_net(name, via_cost=2.0, max_exp=350000) and r.net_components(name) <= 1:
                    if r.route_net(blk, via_cost=2.0, max_exp=350000) and r.net_components(blk) <= 1:
                        unrouted.discard(name)
                        print(f"REPAIR r{rnd} {name}: swap {blk} OK ({time.time()-t0:.0f}s)", flush=True)
                    else:
                        unrouted.discard(name)
                        unrouted.add(blk)
                        print(f"REPAIR r{rnd} {name}: OK, {blk} now unrouted ({time.time()-t0:.0f}s)", flush=True)
                    done = True
                    progress = True
                    pcbnew.SaveBoard(path, b)
                    break
                else:
                    if name in r.geom:
                        r.ripup(name)
                    r.route_net(blk, via_cost=2.0, max_exp=350000)
            if not done and r.route_net(name, via_cost=1.5, max_exp=500000) and r.net_components(name) <= 1:
                unrouted.discard(name)
                progress = True
                pcbnew.SaveBoard(path, b)
                print(f"REPAIR r{rnd} {name}: plain OK ({time.time()-t0:.0f}s)", flush=True)
        print(f"ROUND {rnd} done, unrouted={sorted(unrouted)} ({time.time()-t0:.0f}s)", flush=True)
        if not progress:
            break
    pcbnew.SaveBoard(path, b)
    print("FINAL_UNROUTED:", sorted(unrouted), flush=True)
    print("REPAIR DONE", flush=True)

if __name__ == "__main__":
    main()
