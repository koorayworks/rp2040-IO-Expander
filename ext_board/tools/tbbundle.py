#!/usr/bin/env python3
"""TB bundle in pin order (the two failing nets first, while the
JLEG-bottom-row wall gaps are empty)."""
import pcbnew, os, sys, time
import importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["tbbundle"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b)
r.ingest()
t0 = time.time()
names = ["TB1", "TB2", "TB3", "TB4", "TB5", "TB6"]
for n in names:
    if n in r.geom:
        r.ripup(n)
r.rebuild_copper(); r.rebuild_blockers()
left = []
for n in names:
    if r.net_components(n) <= 1:
        continue
    ok = False
    for vc, exp in ((2.5, 800000), (1.5, 1200000)):
        if r.route_net(n, via_cost=vc, max_exp=exp) and r.net_components(n) <= 1:
            ok = True
            break
        if n in r.geom:
            r.ripup(n)
    if ok:
        pcbnew.SaveBoard(PATH, b)
        print(f"{n}: OK ({time.time()-t0:.0f}s)", flush=True)
    else:
        left.append(n)
        print(f"{n}: FAIL ({time.time()-t0:.0f}s)", flush=True)
pcbnew.SaveBoard(PATH, b)
print("TBBUNDLE DONE left:", left, flush=True)
