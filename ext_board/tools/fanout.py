#!/usr/bin/env python3
"""Fanout reset: rip every routed U1-fanout signal net plus the unrouted
module nets' partial geometry, then re-route the whole set span-first
with repair rounds. USB_VBUS and GND are out of scope (power handled
separately). Saves after each success; final save at the end."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["fanout"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

RIP = ["GPIO3", "GPIO4", "GPIO5", "GPIO6", "GPIO8", "GPIO9", "GPIO10",
       "GPIO11", "GPIO13", "GPIO14", "GPIO28", "GPIO29",
       "TB3", "TB4", "SWDIO", "SWDCLK", "STATUS_LED", "BOOT",
       "USB_D-_C", "USB_D+_C"]
WORK0 = RIP + ["GPIO0", "GPIO1", "GPIO2", "GPIO7", "GPIO12", "GPIO15",
               "GPIO26", "GPIO27", "EX5", "GP24", "GP25", "RESET",
               "TB1", "TB2", "TB5", "TB6", "USB_D-", "USB_D+"]

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    # ripup() removes the objects from both the model and the board
    def remove_from_board(name):
        if name in r.geom:
            r.ripup(name)
    for n in RIP:
        if n in r.geom:
            remove_from_board(n)
            print("ripped", n, flush=True)
    for n in WORK0:
        if n not in RIP and n in r.geom:
            remove_from_board(n)
            print("ripped partial", n, flush=True)
    r.rebuild_copper()
    r.rebuild_blockers()
    unrouted = {n for n in WORK0 if r.net_components(n) > 1}
    print("work list:", sorted(unrouted), flush=True)
    for name in sorted(unrouted, key=lambda n: rt.span_of(r, n)):
        if r.route_net(name, via_cost=2.5, max_exp=800000) and r.net_components(name) <= 1:
            unrouted.discard(name)
            pcbnew.SaveBoard(PATH, b)
            print(f"ROUTE {name}: OK ({time.time()-t0:.0f}s) left={len(unrouted)}", flush=True)
        else:
            if name in r.geom:
                remove_from_board(name)
            print(f"ROUTE {name}: FAIL ({time.time()-t0:.0f}s)", flush=True)
    for rnd in range(6):
        if not unrouted:
            break
        progress = False
        for name in sorted(unrouted, key=lambda n: rt.span_of(r, n)):
            if r.net_components(name) <= 1:
                unrouted.discard(name)
                progress = True
                continue
            blockers = rt.corridor_blockers(r, name, unrouted)
            done = False
            for blk in blockers[:3]:
                objs = list(r.geom.get(blk, {}).get("objects", []))
                r.ripup(blk)
                if r.route_net(name, via_cost=2.0, max_exp=400000) and r.net_components(name) <= 1:
                    if r.route_net(blk, via_cost=2.0, max_exp=400000) and r.net_components(blk) <= 1:
                        print(f"REPAIR r{rnd} {name}: swap {blk} OK ({time.time()-t0:.0f}s)", flush=True)
                    else:
                        unrouted.add(blk)
                        print(f"REPAIR r{rnd} {name}: OK, {blk} now unrouted ({time.time()-t0:.0f}s)", flush=True)
                    unrouted.discard(name)
                    done = True
                    progress = True
                    pcbnew.SaveBoard(PATH, b)
                    break
                else:
                    if name in r.geom:
                        r.ripup(name)
                    r.route_net(blk, via_cost=2.0, max_exp=400000)
            if not done and r.route_net(name, via_cost=1.5, max_exp=600000) and r.net_components(name) <= 1:
                unrouted.discard(name)
                progress = True
                pcbnew.SaveBoard(PATH, b)
                print(f"REPAIR r{rnd} {name}: plain OK ({time.time()-t0:.0f}s)", flush=True)
        print(f"ROUND {rnd} done ({time.time()-t0:.0f}s) unrouted={sorted(unrouted)}", flush=True)
        if not progress:
            break
    pcbnew.SaveBoard(PATH, b)
    print("FINAL_UNROUTED:", sorted(unrouted), flush=True)
    print("FANOUT DONE", flush=True)

if __name__ == "__main__":
    main()
