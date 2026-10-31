#!/usr/bin/env python3
"""Round 5 solver: find a C1 placement (small move / rotation) whose GND pad2
can be bridged to GND with one via + short B.Cu stub, and whose VBUS pad1 can
be re-fed on B.Cu from the kept VBUS stub (12.218,19.493)->via(11.871,19.493).

Method: reuse router.py's 0.05mm raster model (same clearance model that
produced the DRC-clean R3/R4 boards). Base grids are built from a board copy
with C1 and the two old VBUS B.Cu stub segments removed. Candidates are
pruned by pad copper/clearance tests on the raster, via existence, and
courtyard overlap; survivors get real A* stub searches. kicad-cli DRC on
fully built candidates (separate script) is the final oracle.
"""
import pcbnew, os, sys, math, json, heapq
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["r5_solve"]
spec.loader.exec_module(rt)

MM = pcbnew.FromMM
CELL = rt.CELL
START = os.path.join(HERE, "board_step_r5_start.kicad_pcb")
OLD_C1 = (13.40, 19.90)
OLD_STUBS = [((12.625, 19.90), (12.218, 19.493)), ((12.218, 19.493), (11.871, 19.493))]

# pad configs: name -> (pad1 offset, pad2 offset, pad size (sx,sy), courtyard half extents)
CFGS = {
    "EW1W": ((-0.775, 0.0), (0.775, 0.0), (0.90, 0.95), (1.328, 0.581)),
    "EW1E": ((0.775, 0.0), (-0.775, 0.0), (0.90, 0.95), (1.328, 0.581)),
    "NS1N": ((0.0, -0.775), (0.0, 0.775), (0.95, 0.90), (0.581, 1.328)),
    "NS1S": ((0.0, 0.775), (0.0, -0.775), (0.95, 0.90), (0.581, 1.328)),
}


def close(a, b, tol=0.01):
    return abs(a - b) <= tol


def load_base():
    """Board copy with C1 removed and old VBUS B stubs removed; returns (board, R)."""
    b = pcbnew.LoadBoard(START)
    c1 = b.FindFootprintByReference("C1")
    b.Remove(c1)
    # collect first, then remove (KiCad 8 iteration pitfall, cf. heal.py)
    tracks = list(b.GetTracks())
    n_rm = 0
    for t in tracks:
        if t.GetClass() == "PCB_VIA" or t.GetLayer() != pcbnew.B_Cu:
            continue
        if t.GetNetname() != "USB_VBUS":
            continue
        s = (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y))
        e = (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
        for (a, c) in OLD_STUBS:
            if (close(s[0], a[0]) and close(s[1], a[1]) and close(e[0], c[0]) and close(e[1], c[1])) or \
               (close(s[0], c[0]) and close(s[1], c[1]) and close(e[0], a[0]) and close(e[1], a[1])):
                b.Remove(t)
                n_rm += 1
                break
    assert n_rm == 2, f"expected to remove 2 old VBUS stubs, removed {n_rm}"
    r = rt.R(b)
    r.ingest()
    return b, r


def courtyard_bboxes(board):
    """ref -> courtyard bbox (x0,y0,x1,y1) for B-side or PTH footprints (physical bodies on B)."""
    out = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref in ("C1", "JLEG"):
            continue  # JLEG handled per-pad below (its pads-union bbox spans the whole edge)
        is_pth = any(p.GetDrillSize().x > 0 for p in fp.Pads())
        if not (fp.IsFlipped() or is_pth):
            continue
        boxes = []
        for gi in fp.GraphicalItems():
            if gi.GetLayer() in (pcbnew.B_CrtYd, pcbnew.F_CrtYd):
                bb = gi.GetBoundingBox()
                boxes.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                              pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
        if not boxes:
            # fall back to pads bbox
            xs0, ys0, xs1, ys1 = 1e9, 1e9, -1e9, -1e9
            for p in fp.Pads():
                bb = p.GetBoundingBox()
                xs0 = min(xs0, pcbnew.ToMM(bb.GetLeft())); ys0 = min(ys0, pcbnew.ToMM(bb.GetTop()))
                xs1 = max(xs1, pcbnew.ToMM(bb.GetRight())); ys1 = max(ys1, pcbnew.ToMM(bb.GetBottom()))
            boxes = [(xs0, ys0, xs1, ys1)]
        out[ref] = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                    max(b[2] for b in boxes), max(b[3] for b in boxes))
    # JLEG pads are solder lands on the board edge: keep C1 body off them entirely
    jleg = board.FindFootprintByReference("JLEG")
    if jleg is not None:
        for p in jleg.Pads():
            bb = p.GetBoundingBox()
            out[f"JLEG#{p.GetNumber()}"] = (pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                                            pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
    return out


def pad_rec(cx, cy, sx, sy):
    return dict(x0=cx - sx / 2, x1=cx + sx / 2, y0=cy - sy / 2, y1=cy + sy / 2, cx=cx, cy=cy)


def cells_of(r, rec, grow=0.0):
    rec2 = dict(rec)
    if grow:
        rec2 = dict(x0=rec["x0"] - grow, x1=rec["x1"] + grow,
                    y0=rec["y0"] - grow, y1=rec["y1"] + grow, cx=rec["cx"], cy=rec["cy"])
    return r._pad_cells(rec2)


def pad_ok(r, rec, nid):
    """Pad copper cells must be empty/same-net; halo test uses grow=0.05 only:
    the raster stamps (bbox pads, 0.08-radius tracks) already inflate foreign
    copper by ~0.03-0.08mm, so a full 0.10 grow double-counts clearance and
    even rejects the known-DRC-clean current position (measured: pad2 halo
    has 8 foreign cells at (0,0) on the start board). kicad-cli DRC on built
    candidates remains the real oracle."""
    cop = r.copper[2]
    for (y, x) in cells_of(r, rec):
        v = cop[y, x]
        if v != 0 and v != nid:
            return False
        if r.edge_block[y, x]:
            return False
    for (y, x) in cells_of(r, rec, grow=0.05):
        v = cop[y, x]
        if v != 0 and v != nid:
            return False
    return True


def via_free_nid(r, y, x, nid):
    if r.edge_block[y, x]:
        return False
    for L in range(rt.NL):
        if r.copper[L][y, x] not in (0, nid):
            return False
        o1, o2 = r.via_o[L]
        a, bq = o1[y, x], o2[y, x]
        if not ((a == 0 or a == nid) and (bq == 0 or bq == nid)):
            return False
    return True


def via_exists(r, rec2, nid_gnd, reach=1.7):
    x0 = int((rec2["x0"] - reach) / CELL); x1 = int((rec2["x1"] + reach) / CELL)
    y0 = int((rec2["y0"] - reach) / CELL); y1 = int((rec2["y1"] + reach) / CELL)
    best = None
    for yy in range(max(0, y0), min(rt.H - 1, y1) + 1):
        for xx in range(max(0, x0), min(rt.W - 1, x1) + 1):
            if via_free_nid(r, yy, xx, nid_gnd):
                d = math.hypot(xx * CELL - rec2["cx"], yy * CELL - rec2["cy"])
                if best is None or d < best[0]:
                    best = (d, xx * CELL, yy * CELL)
    return best


def astar_layer(r, L, sources, targets, nid, max_exp=120000):
    """Single-layer A* on the raster with router corner-cut rules."""
    tf = r.track_free
    tgt = set(targets)
    if not tgt:
        return None
    src = [s for s in sources]
    inter = [s for s in src if s in tgt]
    if inter:
        return [inter[0]]
    tarr = [(y, x) for (y, x) in tgt]
    INF = float("inf")
    g = {}
    parent = {}
    pq = []
    for (y, x) in src:
        k = (y, x)
        if k in g:
            continue
        g[k] = 0.0
        h = min(math.hypot(y - ty, x - tx) for (ty, tx) in tarr)
        heapq.heappush(pq, (h, 0.0, k))
    exp = 0
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
        y, x = k
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < rt.W and 0 <= ny_ < rt.H):
                    continue
                if not tf(L, ny_, nx_, nid):
                    continue
                if dx != 0 and dy != 0:
                    if not (tf(L, y, nx_, nid) and tf(L, ny_, x, nid)):
                        continue
                    step = 1.41421
                else:
                    step = 1.0
                nk = (ny_, nx_)
                ng = gc + step
                if ng < g.get(nk, INF):
                    g[nk] = ng
                    parent[nk] = k
                    h = min(math.hypot(ny_ - ty, nx_ - tx) for (ty, tx) in tarr)
                    heapq.heappush(pq, (ng + 1.5 * h, ng, nk))
    return None


def path_len_mm(path):
    tot = 0.0
    for a, c in zip(path, path[1:]):
        tot += math.hypot(c[0] - a[0], c[1] - a[1])
    return tot * CELL


def main():
    b0 = pcbnew.LoadBoard(START)
    bodies = courtyard_bboxes(b0)
    b, r = load_base()
    nid_gnd = r.net_ids["GND"]
    nid_vbus = r.net_ids["USB_VBUS"]

    # ---------- Phase A: prune ----------
    cands = []
    steps = [round(-2.0 + 0.2 * i, 2) for i in range(21)]
    for cfg_name, (o1, o2, (sx, sy), (chx, chy)) in CFGS.items():
        for dx in steps:
            for dy in steps:
                cx, cy = OLD_C1[0] + dx, OLD_C1[1] + dy
                p1 = pad_rec(cx + o1[0], cy + o1[1], sx, sy)
                p2 = pad_rec(cx + o2[0], cy + o2[1], sx, sy)
                if not pad_ok(r, p1, nid_vbus):
                    continue
                if not pad_ok(r, p2, nid_gnd):
                    continue
                # courtyard vs other bodies
                cb = (cx - chx, cy - chy, cx + chx, cy + chy)
                clash = False
                for ref, ob in bodies.items():
                    if not (cb[2] <= ob[0] or cb[0] >= ob[2] or cb[3] <= ob[1] or cb[1] >= ob[3]):
                        clash = True
                        break
                if clash:
                    continue
                ve = via_exists(r, p2, nid_gnd)
                if ve is None:
                    continue
                disp = abs(dx) + abs(dy) + (0.0 if cfg_name == "EW1W" else 0.2)
                cands.append(dict(cfg=cfg_name, dx=dx, dy=dy, cx=cx, cy=cy,
                                  via_hint=[ve[1], ve[2]], via_dist=round(ve[0], 3),
                                  disp=round(disp, 3)))
    cands.sort(key=lambda c: (c["disp"], c["via_dist"]))
    print(f"Phase A survivors: {len(cands)}")
    for c in cands[:20]:
        print("  A:", c)

    # ---------- Phase B: stamp pads, real A* for both stubs ----------
    import numpy as np
    sols = []
    tried = 0
    for c in cands:
        if len(sols) >= 10 or tried >= 16:
            break
        tried += 1
        cfg_name = c["cfg"]
        o1, o2, (sx, sy), _ = CFGS[cfg_name]
        cx, cy = c["cx"], c["cy"]
        p1 = pad_rec(cx + o1[0], cy + o1[1], sx, sy)
        p2 = pad_rec(cx + o2[0], cy + o2[1], sx, sy)
        # stamp new pads into a copy of the B copper grid, rebuild layer-2 blockers
        saved_copper = r.copper[2]
        saved_trk = r.trk_o[2]
        saved_via = r.via_o[2]
        newcop = saved_copper.copy()
        for (yy, xx) in cells_of(r, p1):
            newcop[yy, xx] = nid_vbus
        for (yy, xx) in cells_of(r, p2):
            newcop[yy, xx] = nid_gnd
        r.copper[2] = newcop
        r.trk_o[2] = rt.dilate2(newcop, rt.OFF_TRK)
        r.via_o[2] = rt.dilate2(newcop, rt.OFF_VIA)
        try:
            # via targets near pad2 (updated blockers)
            x0 = int((p2["x0"] - 1.7) / CELL); x1 = int((p2["x1"] + 1.7) / CELL)
            y0 = int((p2["y0"] - 1.7) / CELL); y1 = int((p2["y1"] + 1.7) / CELL)
            vtgt = []
            for yy in range(max(0, y0), min(rt.H - 1, y1) + 1):
                for xx in range(max(0, x0), min(rt.W - 1, x1) + 1):
                    if via_free_nid(r, yy, xx, nid_gnd):
                        vtgt.append((yy, xx))
            if not vtgt:
                continue
            src2 = [(y, x) for (y, x) in r.member_cells(p2)]
            gpath = astar_layer(r, 2, src2, vtgt, nid_gnd)
            if gpath is None:
                continue
            via_yx = gpath[-1]
            # stamp GND stub + via, then route VBUS around them
            cells = set()
            for (yy, xx) in gpath:
                cells.add((2, yy, xx))
            vcells = r._stamp_via(via_yx[1] * CELL, via_yx[0] * CELL, nid_gnd)
            gnd_cells = set()
            for (yy, xx) in gpath:
                gnd_cells.add((yy, xx))
            # apply stub cells (track stamp radius) + via cells to layer-2 copper
            cop2 = r.copper[2].copy()
            for (yy, xx) in gnd_cells:
                cop2[yy, xx] = nid_gnd
            for (L2, yy, xx) in vcells:
                if L2 == 2:
                    cop2[yy, xx] = nid_gnd
            # widen stub cells to track stamp (radius 0.08mm like _stamp_track)
            wide = set()
            for (yy, xx) in gnd_cells:
                for ddy in range(-2, 3):
                    for ddx in range(-2, 3):
                        if math.hypot(ddx, ddy) <= 1.6:
                            wide.add((yy + ddy, xx + ddx))
            for (yy, xx) in wide:
                if 0 <= yy < rt.H and 0 <= xx < rt.W:
                    cop2[yy, xx] = nid_gnd
            r.copper[2] = cop2
            r.trk_o[2] = rt.dilate2(cop2, rt.OFF_TRK)
            r.via_o[2] = rt.dilate2(cop2, rt.OFF_VIA)
            # VBUS targets: all B cells already VBUS in base copper
            base = saved_copper
            vt = [(yy, xx) for yy in range(rt.H) for xx in range(rt.W)
                  if base[yy, xx] == nid_vbus]
            # restrict to the neighbourhood of the kept stub to keep A* fast & local
            vt = [(yy, xx) for (yy, xx) in vt
                  if 10.5 <= xx * CELL <= 14.5 and 17.5 <= yy * CELL <= 21.5]
            src1 = [(y, x) for (y, x) in r.member_cells(p1)]
            vpath = astar_layer(r, 2, src1, vt, nid_vbus)
            if vpath is None:
                continue
            sols.append(dict(cfg=cfg_name, dx=c["dx"], dy=c["dy"], cx=cx, cy=cy,
                             via=[via_yx[1] * CELL, via_yx[0] * CELL],
                             gnd_path=[[xx * CELL, yy * CELL] for (yy, xx) in gpath],
                             vbus_path=[[xx * CELL, yy * CELL] for (yy, xx) in vpath],
                             gnd_len=round(path_len_mm(gpath), 3),
                             vbus_len=round(path_len_mm(vpath), 3),
                             disp=c["disp"]))
            print("  B SOL:", sols[-1]["cfg"], "d=", (c["dx"], c["dy"]),
                  "via=", sols[-1]["via"], "gnd_len=", sols[-1]["gnd_len"],
                  "vbus_len=", sols[-1]["vbus_len"], flush=True)
        finally:
            r.copper[2] = saved_copper
            r.trk_o[2] = saved_trk
            r.via_o[2] = saved_via
    sols.sort(key=lambda s: (s["disp"], s["gnd_len"] + s["vbus_len"]))
    json.dump(sols, open(os.path.join(HERE, "r5_solutions.json"), "w"), indent=1)
    print(f"Phase B solutions: {len(sols)} -> tools/r5_solutions.json")


if __name__ == "__main__":
    main()
