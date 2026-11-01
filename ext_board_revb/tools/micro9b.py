#!/usr/bin/env python3
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["micro9b"]; spec.loader.exec_module(mr)
rt = mr.rt
PATH = os.path.join(HERE, "backups/board_micro9.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
def pair(name, i, j, vc=2.0, mx=4000000, tree_from=None):
    pads = r.pad_groups[name]
    srcs = tree_from if tree_from is not None else [i]
    cur = {}
    for s in srcs:
        for L, cs in r.endpoint(name, pads[s]).items():
            cur.setdefault(L, set()).update(cs)
    if tree_from is not None:
        for (L, y, x) in r.geom.get(name, {}).get("cells", set()):
            cur.setdefault(L, set()).add((y, x))
    tgt = r.endpoint(name, pads[j])
    th = r.th_cells.get(name, set())
    path = r.astar_fast(r.net_ids[name], cur, [tgt], th, via_cost=vc, max_exp=mx)
    if path is None:
        print(f"  PAIR {name} {srcs}->{j} vc={vc}: FAIL ({time.time()-t0:.0f}s)", flush=True); return False
    r.commit(name, path, b.FindNet(name))
    print(f"  PAIR {name} {srcs}->{j} vc={vc}: OK comps={r.net_components(name)} ({time.time()-t0:.0f}s)", flush=True)
    return True
def route(name, vcs=(2.0, 5.0), mx=4000000):
    for vc in vcs:
        if r.net_components(name) <= 1: break
        ok = r.route_net(name, via_cost=vc, max_exp=mx)
        print(f"  {name} vc={vc}: ok={ok} comps={r.net_components(name)} ({time.time()-t0:.0f}s)", flush=True)
        if r.net_components(name) <= 1: pcbnew.SaveBoard(PATH, b)
    print(f"{name}: FINAL={r.net_components(name)}", flush=True)
pair("PR1", 1, 2)
pair("PR1", 0, 1, tree_from=[1, 2])
if r.net_components("PR1") > 1:
    pair("PR1", 0, 2, vc=5.0, tree_from=[1, 2])
print(f"PR1: FINAL={r.net_components('PR1')}", flush=True)
pcbnew.SaveBoard(PATH, b)
route("3V3"); route("VBAT"); route("BAT_IN")
print(f"3V3_USB: comps={r.net_components('3V3_USB')}", flush=True)
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("MICRO9B DONE", flush=True)
