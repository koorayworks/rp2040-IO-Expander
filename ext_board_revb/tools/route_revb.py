#!/usr/bin/env python3
"""REV.B routing: connect the new nets with the REV.A grid router.
Only this session's nets are routed/ripped; REV.A geometry is never ripped."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["route_revb"]
spec.loader.exec_module(rt)

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board_revb")
PATH = os.path.join(BASE, "ext_board_revb.kicad_pcb")
TARGETS = ["3V3", "3V3_USB", "VBAT", "3V3_BAT", "PR1", "BOOST_SW", "BAT_IN"]
RIPPABLE = {"BAT_IN", "VBAT", "BOOST_SW", "PR1", "3V3_BAT", "3V3_USB"}  # never "3V3" (holds REV.A geometry)

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    unrouted = set()
    for n in TARGETS:
        c = r.net_components(n)
        print(f"{n}: components={c}", flush=True)
        if c > 1: unrouted.add(n)
    order = (["3V3"] if "3V3" in unrouted else []) + \
        sorted((n for n in unrouted if n != "3V3"), key=lambda n: rt.span_of(r, n))
    for name in order:
        if r.route_net(name, via_cost=2.5, max_exp=800000) and r.net_components(name) <= 1:
            unrouted.discard(name)
            pcbnew.SaveBoard(PATH, b)
            print(f"ROUTE {name}: OK ({time.time()-t0:.0f}s) left={sorted(unrouted)}", flush=True)
        else:
            print(f"ROUTE {name}: FAIL ({time.time()-t0:.0f}s)", flush=True)
    for rnd in range(5):
        if not unrouted: break
        progress = False
        for name in sorted(unrouted, key=lambda n: rt.span_of(r, n)):
            if r.net_components(name) <= 1:
                unrouted.discard(name); progress = True; continue
            blockers = [x for x in rt.corridor_blockers(r, name, unrouted) if x in RIPPABLE]
            done = False
            for blk in blockers[:2]:
                r.ripup(blk)
                if r.route_net(name, via_cost=2.0, max_exp=350000) and r.net_components(name) <= 1:
                    if r.route_net(blk, via_cost=2.0, max_exp=350000) and r.net_components(blk) <= 1:
                        unrouted.discard(name)
                        print(f"REPAIR r{rnd} {name}: swap {blk} OK ({time.time()-t0:.0f}s)", flush=True)
                    else:
                        unrouted.discard(name); unrouted.add(blk)
                        print(f"REPAIR r{rnd} {name}: OK, {blk} now unrouted ({time.time()-t0:.0f}s)", flush=True)
                    done = True; progress = True
                    pcbnew.SaveBoard(PATH, b)
                    break
                else:
                    if name in r.geom: r.ripup(name)
                    r.route_net(blk, via_cost=2.0, max_exp=350000)
            if not done and r.route_net(name, via_cost=1.5, max_exp=500000) and r.net_components(name) <= 1:
                unrouted.discard(name); progress = True
                pcbnew.SaveBoard(PATH, b)
                print(f"REPAIR r{rnd} {name}: plain OK ({time.time()-t0:.0f}s)", flush=True)
        print(f"ROUND {rnd} done, unrouted={sorted(unrouted)} ({time.time()-t0:.0f}s)", flush=True)
        if not progress: break
    # refill zones
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(PATH, b)
    print("FINAL_UNROUTED:", sorted(unrouted), flush=True)
    print("ROUTE DONE", flush=True)

if __name__ == "__main__":
    main()
