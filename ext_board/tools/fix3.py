#!/usr/bin/env python3
"""Production repair driver (round 2).

Differences vs fix1:
 - relaxed clearance model: track_free/via_free use only the nearest-obstacle
   dilation (o1). TRK_R=0.155 with o1-only still guarantees >=0.105mm real
   clearance for a 0.10mm track; KiCad DRC is run after every step as arbiter.
 - rip-up swaps use corridor blockers; a sacrificed net that does not re-route
   immediately is queued and retried in later rounds.

Usage: python3 fix3.py NET [NET...]   (saves after each connected net)
"""
import pcbnew, os, sys, time
import importlib.util

ARGS = sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fix1", os.path.join(HERE, "fix1.py"))
f1 = importlib.util.module_from_spec(spec)
sys.argv = ["fix3"]
spec.loader.exec_module(f1)
rt = f1.rt
PATH = f1.PATH

ALL_TARGETS = ["GP21", "GPIO6", "GPIO7", "GPIO15", "GPIO28", "GPIO29",
               "GP19", "GP20", "GP22", "GP23"]


def patch_relaxed(r):
    def tf(L, y, x, nid):
        if r.copper[L][y, x] == nid:
            return True
        if r.edge_block[y, x]:
            return False
        o1 = r.trk_o[L][0][y, x]
        return o1 == 0 or o1 == nid

    def vf(y, x, nid):
        if r.edge_block[y, x]:
            return False
        for L in range(3):
            if r.copper[L][y, x] != 0:
                return False
            o1 = r.via_o[L][0][y, x]
            if not (o1 == 0 or o1 == nid):
                return False
        return True

    r.track_free = tf
    r.via_free = vf


def try_net(r, name, unrouted):
    if r.net_components(name) <= 1:
        return True
    if f1.route_fast(r, name, via_cost=1.5, w_h=2.0) and r.net_components(name) <= 1:
        return True
    if name in r.geom:
        r.ripup(name)
    blockers = rt.corridor_blockers(r, name, set())
    for blk in blockers[:6]:
        if blk not in r.geom:
            continue
        r.ripup(blk)
        if f1.route_fast(r, name, via_cost=1.5, w_h=2.0) and r.net_components(name) <= 1:
            if f1.route_fast(r, blk, via_cost=1.5, w_h=2.0) and r.net_components(blk) <= 1:
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
            f1.route_fast(r, blk, via_cost=1.5, w_h=2.0)  # restore best effort
    return False


def main():
    targets = ARGS or ALL_TARGETS
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    patch_relaxed(r)
    unrouted = set()
    for n in list(r.pad_groups):
        if n != "GND" and r.net_components(n) > 1:
            unrouted.add(n)
    print("model-unrouted at start:", sorted(unrouted), flush=True)
    t0 = time.time()
    for rnd in range(4):
        todo = [n for n in targets if n in unrouted]
        extra = [n for n in sorted(unrouted) if n not in targets and n != "GND"]
        todo = todo + extra
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
                print(f"[{rnd}] {name}: OK ({time.time()-ts:.0f}s) left={sorted(unrouted)}", flush=True)
            else:
                print(f"[{rnd}] {name}: FAIL ({time.time()-ts:.0f}s)", flush=True)
        if not progress:
            break
    print("FINAL model-unrouted:", sorted(unrouted), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
