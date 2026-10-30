#!/usr/bin/env python3
"""Targeted routing for the remaining unrouted nets (post-heal state).
CC2 is ripped and redone (its path violated the USB-C NPTH hole clearance;
the router model now blocks those holes)."""
import pcbnew, os, math, time, sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["targeted"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

ORDER = ["CC2", "USB_D-_C", "USB_D-", "USB_D+", "EX5", "RESET",
         "GP24", "GP25", "GPIO12", "GPIO15", "GPIO26", "GPIO27",
         "GPIO7", "GPIO2", "GPIO1", "GPIO0",
         "TB1", "TB2", "TB5", "TB6", "USB_VBUS"]

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    if "CC2" in r.geom:
        r.ripup("CC2")
        print("ripped CC2", flush=True)
    for name in ORDER:
        if r.net_components(name) <= 1:
            print(f"SKIP {name}: already connected", flush=True)
            continue
        ok = r.route_net(name, via_cost=2.0, max_exp=350000) and r.net_components(name) <= 1
        if not ok:
            if name in r.geom:
                r.ripup(name)
            blockers = rt.corridor_blockers(r, name, set())
            for blk in blockers[:2]:
                r.ripup(blk)
                if r.route_net(name, via_cost=2.0, max_exp=500000) and r.net_components(name) <= 1:
                    if not (r.route_net(blk, via_cost=2.0, max_exp=350000) and r.net_components(blk) <= 1):
                        print(f"  note: {blk} sacrificed for {name}", flush=True)
                    ok = True
                    break
                else:
                    if name in r.geom:
                        r.ripup(name)
                    r.route_net(blk, via_cost=2.0, max_exp=350000)
        print(f"{name}: {'OK' if ok else 'FAIL'} ({time.time()-t0:.0f}s)", flush=True)
        if ok:
            pcbnew.SaveBoard(PATH, b)
    pcbnew.SaveBoard(PATH, b)
    left = [n for n in ORDER if r.net_components(n) > 1]
    print("STILL_UNROUTED:", left, flush=True)
    print("TARGETED DONE", flush=True)

if __name__ == "__main__":
    main()
