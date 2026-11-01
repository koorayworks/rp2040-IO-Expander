#!/usr/bin/env python3
"""Debug: why can't the micro router leave the mux pads?
Counts via_free / track_free cells in the south basin and measures the
A* reachable set from U4.3 (3V3_USB) and U4.4 (PR1) on B alone and all layers."""
import pcbnew, os, sys, math, heapq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import micro_route as mr

rt = mr.rt
b = pcbnew.LoadBoard(mr.PATH)
r = rt.R(b)
r.ingest()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()

def cell(x, y): return (int(round(y / 0.05)), int(round(x / 0.05)))

# region: south basin x 2..12, y 26..37
nid_usb = r.net_ids["3V3_USB"]
cnt_via = 0; cnt_trk = {0: 0, 1: 0, 2: 0}
for iy in range(int(26 / 0.05), int(37 / 0.05)):
    for ix in range(int(2 / 0.05), int(12 / 0.05)):
        if r.via_free(iy, ix, nid_usb): cnt_via += 1
        for L in range(3):
            if r.track_free(L, iy, ix, nid_usb): cnt_trk[L] += 1
print(f"basin via_free(3V3_USB): {cnt_via} cells; track_free per layer: {cnt_trk}")

# BFS reachable from a pad's endpoint cells (track moves + via moves as in astar)
def reachable(name, rec, maxn=400000):
    nid = r.net_ids[name]
    src = r.endpoint(name, rec)
    seen = set()
    stack = []
    for L, cells in src.items():
        for (y, x) in cells:
            k = (L, y, x)
            if k not in seen:
                seen.add(k); stack.append(k)
    th = r.th_cells.get(name, set())
    while stack and len(seen) < maxn:
        (L, y, x) = stack.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < rt.W and 0 <= ny_ < rt.H): continue
                if not r.track_free(L, ny_, nx_, nid): continue
                if dx != 0 and dy != 0 and not (r.track_free(L, y, nx_, nid) and r.track_free(L, ny_, x, nid)): continue
                k = (L, ny_, nx_)
                if k not in seen:
                    seen.add(k); stack.append(k)
        for oL in range(3):
            if oL == L: continue
            if (y, x) in th or r.via_free(y, x, nid):
                k = (oL, y, x)
                if k not in seen:
                    seen.add(k); stack.append(k)
    return seen

for name in ("PR1", "3V3_USB"):
    for rec in r.pad_groups[name]:
        seen = reachable(name, rec)
        ys = [k[1] for k in seen]; xs = [k[2] for k in seen]
        print(f"{name} pad @({rec['cx']:.2f},{rec['cy']:.2f}): reachable {len(seen)} cells, "
              f"x {min(xs)*0.05:.1f}..{max(xs)*0.05:.1f}, y {min(ys)*0.05:.1f}..{max(ys)*0.05:.1f}, "
              f"layers {sorted(set(k[0] for k in seen))}")
