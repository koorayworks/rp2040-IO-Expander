#!/usr/bin/env python3
"""One net, one huge plain A* attempt. Usage: bigroute.py NET [EXP]"""
import pcbnew, os, sys, time
import importlib.util
TARGET_NET = sys.argv[1] if len(sys.argv) > 1 else None
EXP = int(sys.argv[2]) if len(sys.argv) > 2 else 2500000
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["bigroute"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b)
r.ingest()
name = TARGET_NET
if r.net_components(name) <= 1:
    print(f"{name}: already connected")
else:
    t0 = time.time()
    ok = r.route_net(name, via_cost=2.0, max_exp=EXP) and r.net_components(name) <= 1
    if ok:
        pcbnew.SaveBoard(PATH, b)
        print(f"{name}: OK big ({time.time()-t0:.0f}s)")
    else:
        print(f"{name}: FAIL big ({time.time()-t0:.0f}s) -- board NOT saved")
