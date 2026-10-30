#!/usr/bin/env python3
"""Wall pocket: for a net whose two pad basins are disjoint, find the
closest approach between the basins, histogram the nets occupying the
gap, rip the top occupant, and route. Restores the occupant after.
Usage: wallpocket.py NETNAME"""
import pcbnew, os, sys, time, math
import importlib.util
from collections import deque, Counter

TARGET_NET = sys.argv[1] if len(sys.argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["wallpocket"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
NEVER_RIP = {"3V3", "USB_VBUS", "VSYS", "GND"}

def true_basin(r, name, rec):
    nid = r.net_ids[name]
    ep = r.endpoint(name, rec)
    cells = [(L, y, x) for L in range(3) for (y, x) in ep.get(L, [])]
    seen = set(cells)
    dq = deque(cells)
    tf = r.track_free
    while dq:
        (L, y, x) = dq.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                ny, nx = y + dy, x + dx
                if not (0 <= nx < 361 and 0 <= ny < 871) or (L, ny, nx) in seen:
                    continue
                if not tf(L, ny, nx, nid):
                    continue
                if dx != 0 and dy != 0 and not (tf(L, y, nx, nid) and tf(L, ny, x, nid)):
                    continue
                seen.add((L, ny, nx)); dq.append((L, ny, nx))
        if r.via_free(y, x, nid):
            for L2 in range(3):
                if L2 != L and (L2, y, x) not in seen and tf(L2, y, x, nid):
                    seen.add((L2, y, x)); dq.append((L2, y, x))
    return seen

def main():
    name = TARGET_NET
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    if r.net_components(name) <= 1:
        print(f"{name}: already connected")
        return
    t0 = time.time()
    nid = r.net_ids[name]
    if r.route_net(name, via_cost=2.0, max_exp=300000) and r.net_components(name) <= 1:
        pcbnew.SaveBoard(PATH, b)
        print(f"{name}: OK plain ({time.time()-t0:.0f}s)")
        return
    if name in r.geom:
        r.ripup(name)
    pads = r.pad_groups[name]
    if len(pads) != 2:
        print(f"{name}: {len(pads)} pads -- wallpocket needs exactly 2")
        return
    bA = true_basin(r, name, pads[0])
    bB = true_basin(r, name, pads[1])
    print(f"{name}: basins {len(bA)} / {len(bB)}", flush=True)
    # closest approach: index B cells by (y,x) per layer + via columns
    setB = set(bB)
    best = (1e9, None, None)
    for (L, y, x) in bA:
        for (dy, dx) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2), (3, 0), (-3, 0), (0, 3), (0, -3), (4, 0), (-4, 0), (0, 4), (0, -4)):
            if (L, y + dy, x + dx) in setB:
                d = math.hypot(dy, dx)
                if d < best[0]:
                    best = (d, (L, y, x), (L, y + dy, x + dx))
    if best[1] is None:
        # via-column proximity: same (y,x) in both basins on different
        # layers, but via_free fails -> rip whoever blocks the vias there
        posA = {(y, x) for (_, y, x) in bA}
        posB = {(y, x) for (_, y, x) in bB}
        common = posA & posB
        print(f"{name}: no same-layer proximity; shared columns: {len(common)}", flush=True)
        if common:
            inv2 = {v: k for k, v in r.net_ids.items()}
            vcnt = Counter()
            for (y, x) in common:
                for L2 in range(3):
                    for slot in (0, 1):
                        v = r.via_o[L2][slot][y, x]
                        if v not in (0, nid):
                            vcnt[inv2.get(v, str(v))] += 1
            vcands = [n for (n, _) in vcnt.most_common(6) if n not in NEVER_RIP and n != name and n in r.geom]
            print(f"{name}: via blockers: {vcnt.most_common(6)} cands={vcands}", flush=True)
            for blk in vcands[:3]:
                r.ripup(blk)
                ok = r.route_net(name, via_cost=2.0, max_exp=500000) and r.net_components(name) <= 1
                if not ok and name in r.geom:
                    r.ripup(name)
                restored = r.route_net(blk, via_cost=2.0, max_exp=300000) and r.net_components(blk) <= 1
                if ok:
                    pcbnew.SaveBoard(PATH, b)
                    print(f"{name}: OK via-column rip {blk} (restored={restored}) ({time.time()-t0:.0f}s)")
                    return
                print(f"{name}: via-column rip {blk} failed (restored={restored})", flush=True)
        print(f"{name}: FAIL ({time.time()-t0:.0f}s) -- board NOT saved")
        return
    d, cA, cB = best
    print(f"{name}: closest approach {d * 0.05:.2f}mm at A{cA} B{cB}", flush=True)
    # histogram nets in the corridor between cA and cB (all layers, r=0.5mm)
    inv = {v: k for k, v in r.net_ids.items()}
    mx, my = (cA[2] + cB[2]) / 2 * 0.05, (cA[1] + cB[1]) / 2 * 0.05
    cnt = Counter()
    for L in range(3):
        for yi in range(int((my - 0.6) / 0.05), int((my + 0.6) / 0.05)):
            for xi in range(int((mx - 0.6) / 0.05), int((mx + 0.6) / 0.05)):
                if 0 <= xi < 361 and 0 <= yi < 871:
                    v = r.copper[L][yi, xi]
                    if v not in (0, nid):
                        cnt[inv.get(v, str(v))] += 1
    cands = [n for (n, _) in cnt.most_common(6) if n not in NEVER_RIP and n != name and n in r.geom]
    print(f"{name}: corridor nets: {cnt.most_common(6)} cands={cands}", flush=True)
    for blk in cands[:3]:
        r.ripup(blk)
        ok = r.route_net(name, via_cost=2.0, max_exp=500000) and r.net_components(name) <= 1
        if not ok and name in r.geom:
            r.ripup(name)
        restored = r.route_net(blk, via_cost=2.0, max_exp=400000) and r.net_components(blk) <= 1
        if ok:
            pcbnew.SaveBoard(PATH, b)
            print(f"{name}: OK via rip {blk} (restored={restored}) ({time.time()-t0:.0f}s)")
            return
        print(f"{name}: rip {blk} did not open the wall (restored={restored})", flush=True)
    print(f"{name}: FAIL ({time.time()-t0:.0f}s) -- board NOT saved")

if __name__ == "__main__":
    main()
