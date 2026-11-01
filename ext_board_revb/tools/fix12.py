#!/usr/bin/env python3
"""fix12: rip 3V3 v14 tail, micro-route 3V3 tail + PR1 U4.4 link on fix11 board."""
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["fix12"]; spec.loader.exec_module(mr)
rt = mr.rt
TM = pcbnew.ToMM
PATH = os.path.join(HERE, "backups/board_micro9.kicad_pcb")
b = pcbnew.LoadBoard(PATH)

def ep(t):
    a, c = t.GetStart(), t.GetEnd()
    return (TM(a.x), TM(a.y)), (TM(c.x), TM(c.y))
def close(p, q, tol=0.011): return abs(p[0]-q[0]) < tol and abs(p[1]-q[1]) < tol
def seg_is(t, net, p, q):
    if t.GetClass() == "PCB_VIA" or t.GetNetname() != net: return False
    a, c = ep(t)
    return (close(a, p) and close(c, q)) or (close(a, q) and close(c, p))

TAIL = [((5.18,33.62),(5.38,34.00)), ((5.38,34.00),(5.40,34.10)), ((5.40,34.10),(5.40,34.80)),
        ((5.40,34.80),(4.95,34.80)), ((4.95,34.80),(4.95,34.55))]
to_delete = [t for t in list(b.GetTracks()) if any(seg_is(t, "3V3", p, q) for (p, q) in TAIL)]
print("rip tail:", len(to_delete), flush=True)
for t in to_delete: b.Remove(t)

r = rt.R(b); r.ingest()
t0 = time.time()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
print(f"sampled ({time.time()-t0:.0f}s)", flush=True)
for net in ("3V3", "PR1", "3V3_USB"):
    print(f"{net}: components={r.net_components(net)} groups={len(r.pad_groups[net])}", flush=True)
    for i, g in enumerate(r.pad_groups[net]):
        print(f"   group{i}: cx={g['cx']:.2f} cy={g['cy']:.2f}", flush=True)

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

def route(name, vcs=(2.0, 5.0, 1.2), mx=4000000):
    for vc in vcs:
        if r.net_components(name) <= 1: break
        ok = r.route_net(name, via_cost=vc, max_exp=mx)
        print(f"  {name} vc={vc}: ok={ok} comps={r.net_components(name)} ({time.time()-t0:.0f}s)", flush=True)
        if r.net_components(name) <= 1: pcbnew.SaveBoard(PATH, b)
    print(f"{name}: FINAL={r.net_components(name)}", flush=True)

route("3V3")
route("PR1")
f = pcbnew.ZONE_FILLER(b); f.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("FIX12 DONE", flush=True)
