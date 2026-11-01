#!/usr/bin/env python3
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["micro8"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = os.path.join(HERE, "backups/board_micro6.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
name = "3V3_USB"
pads = r.pad_groups[name]
# tree source: all committed geometry cells + endpoints of pads 1,2
cur = {}
for (L, y, x) in r.geom.get(name, {}).get("cells", set()):
    cur.setdefault(L, set()).add((y, x))
for i in (1, 2):
    for L, cs in r.endpoint(name, pads[i]).items():
        cur.setdefault(L, set()).update(cs)
tgt = r.endpoint(name, pads[3])
th = r.th_cells.get(name, set())
for vc in (2.0, 5.0, 1.2):
    path = r.astar_fast(r.net_ids[name], cur, [tgt], th, via_cost=vc, max_exp=6000000)
    print(f"  tree->R4.1 vc={vc}: {'OK' if path else 'FAIL'} ({time.time()-t0:.0f}s)", flush=True)
    if path:
        r.commit(name, path, b.FindNet(name))
        break
print("3V3_USB comps:", r.net_components(name), flush=True)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("MICRO8 DONE", flush=True)
