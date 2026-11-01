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
pk = flood(ends[1])
print("Pocket map: #=pocket X=foreign copper .=free (any layer), cols x=0..11 step0.1, rows y=25..37 step0.2")
hdr = "      " + "".join(str(int(x) % 10) for x in np.arange(0, 11, 0.1))
print(hdr)
for gy in range(int(25/0.2), int(37/0.2)):
    cy = gy*4
    row = ""
    for gx in range(0, int(11/0.1)):
        cx = gx*2
        if any(pk[L][cy, cx] for L in range(3)): row += "#"
        elif any(r.copper[L][cy, cx] != 0 for L in range(3)): row += "X"
        elif any(free[L][cy, cx] for L in range(3)): row += "."
        else: row += " "
    print(f"y={gy*0.2:5.1f} {row}")
