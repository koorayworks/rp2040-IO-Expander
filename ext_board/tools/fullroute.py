#!/usr/bin/env python3
"""Full reset re-route: rip ALL non-GND signal geometry, then route in a
constraint-first order (power, USB west corridor, module locals, long
east crossings, TB bundle, short hops, then GPIOs by span). Saves after
every success so a VM rollback only loses the in-flight net."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["fullroute"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

ORDER_HEAD = ["USB_VBUS", "3V3", "VSYS",
              "USB_D-_C", "USB_D+_C", "USB_D-", "USB_D+",
              "RESET", "BOOT", "STATUS_LED", "SWDIO", "SWDCLK",
              "CC1", "CC2",
              "GP24", "GP25",
              "TB1", "TB2", "TB3", "TB4", "TB5", "TB6",
              "EX1", "EX2", "EX3", "EX4", "EX5", "EX6",
              "GP17", "GP18", "GP19", "GP20", "GP21", "GP22", "GP23"]

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    for name in list(r.geom.keys()):
        if name != "GND":
            r.ripup(name)
    r.rebuild_copper()
    r.rebuild_blockers()
    print("all signal geometry ripped", flush=True)
    names = [n for n in r.pad_groups if n != "GND"]
    head = [n for n in ORDER_HEAD if n in names]
    tail = sorted([n for n in names if n not in ORDER_HEAD], key=lambda n: rt.span_of(r, n))
    order = head + tail
    unrouted = set()
    for name in order:
        if r.net_components(name) <= 1:
            continue
        if r.route_net(name, via_cost=2.5, max_exp=800000) and r.net_components(name) <= 1:
            pcbnew.SaveBoard(PATH, b)
            print(f"ROUTE {name}: OK ({time.time()-t0:.0f}s)", flush=True)
        else:
            if name in r.geom:
                r.ripup(name)
            unrouted.add(name)
            print(f"ROUTE {name}: FAIL ({time.time()-t0:.0f}s)", flush=True)
    pcbnew.SaveBoard(PATH, b)
    print("FULLROUTE FIRST PASS DONE, unrouted:", sorted(unrouted), flush=True)

if __name__ == "__main__":
    main()
