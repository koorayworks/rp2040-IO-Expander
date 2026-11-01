#!/usr/bin/env python3
"""fix13: PR1 U4.4 link via pair(tree_from=cluster)."""
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["fix13"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = os.path.join(HERE, "backups/board_micro9.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
print(f"sampled ({time.time()-t0:.0f}s) PR1 comps={r.net_components('PR1')}", flush=True)

def pair(name, j, vc=2.0, mx=6000000, tree_from=(1, 2)):
    pads = r.pad_groups[name]
    cur = {}
    for s in tree_from:
        for L, cs in r.endpoint(name, pads[s]).items():
            cur.setdefault(L, set()).update(cs)
    for (L, y, x) in r.geom.get(name, {}).get("cells", set()):
        cur.setdefault(L, set()).add((y, x))
    tgt = r.endpoint(name, pads[j])
    th = r.th_cells.get(name, set())
    path = r.astar_fast(r.net_ids[name], cur, [tgt], th, via_cost=vc, max_exp=mx)
    if path is None:
        print(f"  PAIR ->{j} vc={vc}: FAIL ({time.time()-t0:.0f}s)", flush=True); return False
    r.commit(name, path, b.FindNet(name))
    print(f"  PAIR ->{j} vc={vc}: OK comps={r.net_components(name)} ({time.time()-t0:.0f}s)", flush=True)
    return True

for vc in (2.0, 5.0, 1.2, 0.6):
    if r.net_components("PR1") <= 1: break
    if pair("PR1", 0, vc=vc):
        pcbnew.SaveBoard(PATH, b)
print(f"PR1 FINAL={r.net_components('PR1')}", flush=True)
if r.net_components("PR1") <= 1:
    f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
    pcbnew.SaveBoard(PATH, b)
print("FIX13 DONE", flush=True)
