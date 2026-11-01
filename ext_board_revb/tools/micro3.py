#!/usr/bin/env python3
"""Reorder experiment: 3V3_USB first on the pre-micro2 board state."""
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["micro3"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "backups/test_reorder.kicad_pcb")
NETS = ["3V3_USB", "VBAT", "PR1", "3V3"]
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
print(f"sampled in {time.time()-t0:.0f}s", flush=True)
for net in NETS:
    print(f"{net}: components={r.net_components(net)}", flush=True)
for net in NETS:
    for vc in (2.0, 5.0, 1.2):
        if r.net_components(net) <= 1: break
        ok = r.route_net(net, via_cost=vc, max_exp=4000000)
        print(f"  {net} vc={vc}: ok={ok} comps={r.net_components(net)} ({time.time()-t0:.0f}s)", flush=True)
        if r.net_components(net) <= 1:
            pcbnew.SaveBoard(PATH, b); break
    print(f"{net}: FINAL={r.net_components(net)}", flush=True)
print("MICRO3 DONE", flush=True)
