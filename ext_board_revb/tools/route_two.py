#!/usr/bin/env python3
"""Route BAT_IN + VBAT only, no rip-up of anything."""
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec); sys.argv = ["route_two"]; spec.loader.exec_module(rt)
BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board_revb")
PATH = os.path.join(BASE, "ext_board_revb.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
order = sys.argv[1:] if len(sys.argv) > 1 else ["BAT_IN", "VBAT"]
for name in order:
    print(f"{name}: components={r.net_components(name)}", flush=True)
for name in order:
    for vc in (2.5, 6.0, 1.2):
        if r.net_components(name) <= 1: break
        ok = r.route_net(name, via_cost=vc, max_exp=1200000)
        print(f"  {name} vc={vc}: ok={ok} components={r.net_components(name)}", flush=True)
        if r.net_components(name) <= 1:
            pcbnew.SaveBoard(PATH, b); break
print("done", flush=True)
