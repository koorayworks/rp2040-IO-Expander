#!/usr/bin/env python3
"""Bundle endgame: rip sibling bundles and re-lay them together so the
A* can assign parallel lanes instead of musical-chairs swaps.
Bundles: TB1..TB6 (pin order), then GPIO6+GPIO7 (6 first)."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["bundles"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

def route_seq(b, r, names, label):
    t0 = time.time()
    for n in names:
        if n in r.geom:
            r.ripup(n)
    r.rebuild_copper()
    r.rebuild_blockers()
    left = []
    for n in names:
        if r.net_components(n) <= 1:
            continue
        ok = False
        for vc, exp in ((2.5, 800000), (1.5, 800000)):
            if r.route_net(n, via_cost=vc, max_exp=exp) and r.net_components(n) <= 1:
                ok = True
                break
            if n in r.geom:
                r.ripup(n)
        if ok:
            pcbnew.SaveBoard(PATH, b)
            print(f"{label} {n}: OK ({time.time()-t0:.0f}s)", flush=True)
        else:
            left.append(n)
            print(f"{label} {n}: FAIL ({time.time()-t0:.0f}s)", flush=True)
    return left

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    left1 = route_seq(b, r, ["TB3", "TB4", "TB5", "TB6", "TB2", "TB1"], "TB")
    left2 = route_seq(b, r, ["GPIO6", "GPIO7"], "GPIO")
    pcbnew.SaveBoard(PATH, b)
    print("BUNDLES DONE left:", left1 + left2, flush=True)

if __name__ == "__main__":
    main()
