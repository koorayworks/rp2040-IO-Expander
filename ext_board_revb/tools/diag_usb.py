import pcbnew, os, sys, math
import importlib.util
import numpy as np
from scipy import ndimage
HERE = os.path.abspath(".")
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["diag"]; spec.loader.exec_module(mr)
rt = mr.rt
b = pcbnew.LoadBoard("../ext_board_revb.kicad_pcb")
r = rt.R(b); r.ingest()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
name = "3V3_USB"; nid = r.net_ids[name]
free = []
for L in range(3):
    o1, o2 = r.trk_o[L]
    m = ((o1 == 0) | (o1 == nid)) & ((o2 == 0) | (o2 == nid)) & ~r.edge_block
    m |= (r.copper[L] == nid)
    free.append(m)
via_ok = np.ones_like(free[0])
for L in range(3):
    o1, o2 = r.via_o[L]
    via_ok &= ((o1 == 0) | (o1 == nid)) & ((o2 == 0) | (o2 == nid)) & (r.copper[L] == 0)
via_ok &= ~r.edge_block
struct = np.ones((3,3), dtype=bool)
def flood(src):
    cur = [np.zeros_like(free[0]) for _ in range(3)]
    for L, cs in src.items():
        for (y, x) in cs: cur[L][y, x] = True
    while True:
        new = [cur[L] | (ndimage.binary_dilation(cur[L], struct) & free[L]) for L in range(3)]
        bridge = (new[0] | new[1] | new[2]) & via_ok
        for L in range(3): new[L] |= bridge
        if all((new[L] == cur[L]).all() for L in range(3)): return cur
        cur = new
pads = r.pad_groups[name]
ends = [r.endpoint(name, p) for p in pads]
floods = [flood(e) for e in ends]
print("floods done", flush=True)
CELL = rt.CELL
id2name = {v: k for k, v in r.net_ids.items()}
LAYN = {0:"F",1:"In2",2:"B"}
for (i, j) in ((0,1),(0,3),(1,3)):
    for L in range(3):
        if not floods[j][L].any() or not floods[i][L].any(): continue
        dt = ndimage.distance_transform_edt(~floods[j][L])
        vals = np.where(floods[i][L], dt, 9e9)
        k = int(vals.argmin()); d = float(vals.flat[k])
        y, x = np.unravel_index(k, vals.shape)
        nets = set()
        rad = max(int(d)+2, 3)
        for yy in range(max(0,y-rad), min(rt.H, y+rad+1)):
            for xx in range(max(0,x-rad), min(rt.W, x+rad+1)):
                if math.hypot(yy-y, xx-x) <= rad:
                    for LL in range(3):
                        v = r.copper[LL][yy, xx]
                        if v not in (0, nid): nets.add(id2name.get(v, str(v)))
        print(f"pair {i}-{j} L{LAYN[L]}: gap {d*CELL:.2f}mm at ({x*CELL:.2f},{y*CELL:.2f}) obstacles: {sorted(nets)}", flush=True)
print("DIAG DONE", flush=True)
