#!/usr/bin/env python3
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["micro9c"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = os.path.join(HERE, "backups/board_micro9.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
name = "PR1"
pads = r.pad_groups[name]
cur = {}
for s in (1, 2):
    for L, cs in r.endpoint(name, pads[s]).items():
        cur.setdefault(L, set()).update(cs)
for (L, y, x) in r.geom.get(name, {}).get("cells", set()):
    cur.setdefault(L, set()).add((y, x))
tgt = r.endpoint(name, pads[0])
th = r.th_cells.get(name, set())
for vc in (2.0, 5.0, 1.2, 8.0):
    if r.net_components(name) <= 1: break
    path = r.astar_fast(r.net_ids[name], cur, [tgt], th, via_cost=vc, max_exp=8000000)
    print(f"  tree->U4.4 vc={vc}: {'OK' if path else 'FAIL'} ({time.time()-t0:.0f}s)", flush=True)
    if path:
        r.commit(name, path, b.FindNet(name)); break
print(f"PR1: FINAL={r.net_components(name)}", flush=True)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("MICRO9C DONE", flush=True)
