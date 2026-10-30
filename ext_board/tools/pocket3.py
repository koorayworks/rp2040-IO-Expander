#!/usr/bin/env python3
"""Pocket escape v3: like pocket2, but when single-blocker rips fail,
try ripping PAIRS of top via-blockers (carpeted pockets need two nets
moved at once). Restores blockers afterwards; any that fail to restore
are reported (they rejoin the work queue).
Usage: pocket3.py NETNAME [PROTECT_NET ...]"""
import pcbnew, os, sys, time
import importlib.util
from collections import deque, Counter

TARGET_NET = sys.argv[1] if len(sys.argv) > 1 else None
PROTECT = set(sys.argv[2:])
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["pocket3"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
NEVER_RIP = {"3V3", "USB_VBUS", "VSYS", "GND"} | PROTECT

def basin_of(r, name, rec):
    nid = r.net_ids[name]
    ep = r.endpoint(name, rec)
    cells = [(L, y, x) for L in range(3) for (y, x) in ep.get(L, [])]
    seen = set(cells)
    dq = deque(cells)
    while dq:
        (L, y, x) = dq.popleft()
        for (dy, dx) in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= nx < 361 and 0 <= ny < 871 and (L, ny, nx) not in seen and r.track_free(L, ny, nx, nid):
                seen.add((L, ny, nx)); dq.append((L, ny, nx))
        if r.via_free(y, x, nid):
            for L2 in range(3):
                if L2 != L and (L2, y, x) not in seen and r.track_free(L2, y, x, nid):
                    seen.add((L2, y, x)); dq.append((L2, y, x))
    return seen

def try_route(r, name, vc=2.0, exp=500000):
    return r.route_net(name, via_cost=vc, max_exp=exp) and r.net_components(name) <= 1

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
    if try_route(r, name, 2.0, 400000):
        pcbnew.SaveBoard(PATH, b)
        print(f"{name}: OK plain ({time.time()-t0:.0f}s)")
        return
    if name in r.geom:
        r.ripup(name)
    inv = {v: k for k, v in r.net_ids.items()}
    worst = None
    for rec in r.pad_groups[name]:
        bs = basin_of(r, name, rec)
        if worst is None or len(bs) < len(worst[0]):
            worst = (bs, rec)
    basin, rec = worst
    via_wall = Counter()
    for (L, y, x) in basin:
        if L != 0:
            continue
        if not r.via_free(y, x, nid):
            for L2 in range(3):
                v1 = r.via_o[L2][0][y, x]
                if v1 not in (0, nid):
                    via_wall[inv.get(v1, str(v1))] += 1
    cands = [n for (n, _) in via_wall.most_common(8) if n not in NEVER_RIP and n != name and n in r.geom]
    print(f"{name}: basin={len(basin)} cands={cands}", flush=True)
    def attempt(rips):
        for blk in rips:
            r.ripup(blk)
        ok = try_route(r, name, 2.0, 500000) or try_route(r, name, 1.2, 500000)
        if not ok and name in r.geom:
            r.ripup(name)
        restored = []
        lost = []
        for blk in rips:
            if try_route(r, blk, 2.0, 400000):
                restored.append(blk)
            else:
                if blk in r.geom:
                    r.ripup(blk)
                lost.append(blk)
        return ok, restored, lost
    for blk in cands[:3]:
        ok, restored, lost = attempt([blk])
        if ok:
            pcbnew.SaveBoard(PATH, b)
            print(f"{name}: OK rip {blk} restored={restored} lost={lost} ({time.time()-t0:.0f}s)")
            return
    pairs = []
    if len(cands) >= 2:
        pairs = [(cands[0], cands[1]), (cands[0], cands[2]), (cands[1], cands[2])] if len(cands) >= 3 else [(cands[0], cands[1])]
    for (b1, b2) in pairs:
        ok, restored, lost = attempt([b1, b2])
        if ok:
            pcbnew.SaveBoard(PATH, b)
            print(f"{name}: OK rip pair {b1}+{b2} restored={restored} lost={lost} ({time.time()-t0:.0f}s)")
            return
    print(f"{name}: FAIL ({time.time()-t0:.0f}s) -- board NOT saved")

if __name__ == "__main__":
    main()
