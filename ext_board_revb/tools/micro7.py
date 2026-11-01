#!/usr/bin/env python3
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["micro7"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = os.path.join(HERE, "backups/board_micro6.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
kill = [t for t in b.GetTracks() if t.GetNetname() == "3V3_USB"]
for t in kill: b.Remove(t)
print("ripped 3V3_USB:", len(kill), flush=True)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
print("PR1 comps:", r.net_components("PR1"), flush=True)
for vc in (2.0, 5.0, 1.2):
    if r.net_components("PR1") <= 1: break
    ok = r.route_net("PR1", via_cost=vc, max_exp=4000000)
    print(f"  PR1 vc={vc}: ok={ok} comps={r.net_components('PR1')} ({time.time()-t0:.0f}s)", flush=True)
    if r.net_components("PR1") <= 1: pcbnew.SaveBoard(PATH, b)
def connect_pair(name, i, j, vc=2.0, mx=4000000):
    pads = r.pad_groups[name]
    cur = {L: set(cs) for L, cs in r.endpoint(name, pads[i]).items()}
    tgt = r.endpoint(name, pads[j])
    th = r.th_cells.get(name, set())
    path = r.astar_fast(r.net_ids[name], cur, [tgt], th, via_cost=vc, max_exp=mx)
    if path is None:
        print(f"  PAIR {name} {i}->{j}: FAIL", flush=True); return False
    r.commit(name, path, b.FindNet(name))
    print(f"  PAIR {name} {i}->{j}: OK comps={r.net_components(name)}", flush=True)
    return True
connect_pair("3V3_USB", 1, 2)
connect_pair("3V3_USB", 1, 3)
print("3V3_USB comps:", r.net_components("3V3_USB"), flush=True)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("MICRO7 DONE", flush=True)
