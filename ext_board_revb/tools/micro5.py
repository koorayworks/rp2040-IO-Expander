#!/usr/bin/env python3
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["micro5"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = os.path.join(HERE, "backups/board_micro5.kicad_pcb")
PLAN = [("3V3_USB", (2.0, 5.0), 20000000), ("3V3", (2.0,), 4000000), ("VBAT", (2.0, 5.0), 4000000),
        ("PR1", (2.0,), 4000000), ("3V3_BAT", (2.0, 5.0), 4000000), ("BAT_IN", (2.0,), 4000000),
        ("BOOST_SW", (2.0,), 4000000)]
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
for net, vcs, mx in PLAN:
    print(f"{net}: components={r.net_components(net)}", flush=True)
for net, vcs, mx in PLAN:
    for vc in vcs:
        if r.net_components(net) <= 1: break
        ok = r.route_net(net, via_cost=vc, max_exp=mx)
        print(f"  {net} vc={vc}: ok={ok} comps={r.net_components(net)} ({time.time()-t0:.0f}s)", flush=True)
        if r.net_components(net) <= 1:
            pcbnew.SaveBoard(PATH, b); break
    print(f"{net}: FINAL={r.net_components(net)}", flush=True)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("MICRO5 DONE", flush=True)
