#!/usr/bin/env python3
"""Micro-router driver v2: exact sampled copper (from micro_route.py),
custom net order: 3V3 first (hardest), then 3V3_USB, VBAT, PR1."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec)
sys.argv = ["micro2"]
spec.loader.exec_module(mr)
rt = mr.rt

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board_revb")
PATH = os.path.join(BASE, "ext_board_revb.kicad_pcb")

def main():
    nets = sys.argv[1:] or ["3V3", "3V3_USB", "VBAT", "PR1"]
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    r.copper = mr.sample_copper(b, r)
    r.pads_copper = [c.copy() for c in r.copper]
    r.rebuild_blockers()
    print(f"sampled copper in {time.time()-t0:.0f}s", flush=True)
    for net in nets:
        print(f"{net}: components={r.net_components(net)}", flush=True)
    for net in nets:
        for vc in (2.0, 5.0, 1.2, 8.0):
            if r.net_components(net) <= 1:
                break
            ok = r.route_net(net, via_cost=vc, max_exp=4000000)
            print(f"  {net} via_cost={vc}: ok={ok} components={r.net_components(net)} ({time.time()-t0:.0f}s)", flush=True)
            if r.net_components(net) <= 1:
                pcbnew.SaveBoard(PATH, b)
                break
        print(f"{net}: FINAL components={r.net_components(net)}", flush=True)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(PATH, b)
    print("MICRO2 DONE", flush=True)

if __name__ == "__main__":
    main()
