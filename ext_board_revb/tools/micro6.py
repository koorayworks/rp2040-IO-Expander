#!/usr/bin/env python3
"""Smart-order rebuild: cage-prone nets first, pair-connector for 3V3_USB."""
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["micro6"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = os.path.join(HERE, "backups/board_micro6.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
net_obj_cache = {}
def connect_pair(name, src_pad_idx, tgt_pad_idx, vc=2.0, mx=4000000):
    pads = r.pad_groups[name]
    cur = {L: set(cs) for L, cs in r.endpoint(name, pads[src_pad_idx]).items()}
    tgt = r.endpoint(name, pads[tgt_pad_idx])
    th = r.th_cells.get(name, set())
    path = r.astar_fast(r.net_ids[name], cur, [tgt], th, via_cost=vc, max_exp=mx)
    if path is None:
        print(f"  PAIR {name} {src_pad_idx}->{tgt_pad_idx}: FAIL ({time.time()-t0:.0f}s)", flush=True)
        return False
    r.commit(name, path, b.FindNet(name))
    print(f"  PAIR {name} {src_pad_idx}->{tgt_pad_idx}: OK comps={r.net_components(name)} ({time.time()-t0:.0f}s)", flush=True)
    return True
def route(name, vcs=(2.0, 5.0), mx=4000000):
    for vc in vcs:
        if r.net_components(name) <= 1: break
        ok = r.route_net(name, via_cost=vc, max_exp=mx)
        print(f"  {name} vc={vc}: ok={ok} comps={r.net_components(name)} ({time.time()-t0:.0f}s)", flush=True)
        if r.net_components(name) <= 1:
            pcbnew.SaveBoard(PATH, b); break
    print(f"{name}: FINAL={r.net_components(name)}", flush=True)
# 1. cage-prone small nets first
route("BOOST_SW")
pcbnew.SaveBoard(PATH, b)
route("3V3_BAT")
pcbnew.SaveBoard(PATH, b)
# 2. 3V3_USB pocket legs: pads: 0=U2.5, 1=U4.3, 2=U4.5, 3=R4.1
print("3V3_USB legs:", flush=True)
connect_pair("3V3_USB", 1, 2)
connect_pair("3V3_USB", 1, 3)
route("3V3_USB", vcs=(2.0,), mx=2000000)  # will try U2.5 legs; may partially fail
print(f"3V3_USB after legs: comps={r.net_components('3V3_USB')}", flush=True)
pcbnew.SaveBoard(PATH, b)
# 3. the rest
route("3V3")
route("VBAT")
route("PR1")
route("BAT_IN")
print(f"3V3_USB end: comps={r.net_components('3V3_USB')}", flush=True)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("MICRO6 DONE", flush=True)
