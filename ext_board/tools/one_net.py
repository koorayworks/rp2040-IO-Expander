#!/usr/bin/env python3
"""Route ONE net in a fresh process. Saves only if the target net ends up
connected (a sacrificed blocker, if any, is reported so the driver loop
can re-queue it). Usage: one_net.py NETNAME"""
import pcbnew, os, sys, time
import importlib.util

TARGET_NET = sys.argv[1] if len(sys.argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["one_net"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

def main():
    name = TARGET_NET
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    if r.net_components(name) <= 1:
        print(f"{name}: already connected")
        return
    t0 = time.time()
    ok = r.route_net(name, via_cost=2.0, max_exp=350000) and r.net_components(name) <= 1
    sacrificed = None
    if not ok:
        if name in r.geom:
            r.ripup(name)
        blockers = rt.corridor_blockers(r, name, set())
        for blk in blockers[:2]:
            r.ripup(blk)
            if r.route_net(name, via_cost=2.0, max_exp=500000) and r.net_components(name) <= 1:
                if not (r.route_net(blk, via_cost=2.0, max_exp=350000) and r.net_components(blk) <= 1):
                    sacrificed = blk
                ok = True
                break
            else:
                if name in r.geom:
                    r.ripup(name)
                r.route_net(blk, via_cost=2.0, max_exp=350000)
    if ok:
        pcbnew.SaveBoard(PATH, b)
        print(f"{name}: OK ({time.time()-t0:.0f}s)" + (f" sacrificed={sacrificed}" if sacrificed else ""))
    else:
        print(f"{name}: FAIL ({time.time()-t0:.0f}s) -- board NOT saved")

if __name__ == "__main__":
    main()
