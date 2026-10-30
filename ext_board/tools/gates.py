#!/usr/bin/env python3
"""Draw parallel gate-escape stubs for the sealed connector pads
(J2 mid-row on F.Cu heading south; J4 mid pins on B.Cu heading south),
then route the affected nets. Stubs are model-checked cell by cell."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["gates"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

# (net, x, y_from, y_to, layer)
STUBS = [
    ("CC1", 7.75, 0.725, 3.4, 0),
    ("USB_D+_C", 8.75, 0.725, 3.4, 0),
    ("USB_D+_C", 9.75, 0.725, 3.4, 0),
    ("CC2", 10.75, 0.725, 3.4, 0),
    ("EX1", 7.75, 15.65, 18.2, 2),
    ("EX3", 8.75, 15.65, 18.2, 2),
    ("EX4", 9.25, 15.65, 18.2, 2),
    ("EX5", 9.75, 15.65, 18.2, 2),
]
ROUTE_AFTER = ["CC1", "CC2", "USB_D+_C", "EX1", "EX3", "EX4", "EX5"]

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    for (net, x, y0, y1, L) in STUBS:
        nid = r.net_ids[net]
        steps = max(2, int(abs(y1 - y0) / 0.05))
        ok = True
        for i in range(steps + 1):
            tt = i / steps
            sy = y0 + (y1 - y0) * tt
            gx, gy = int(round(x / 0.05)), int(round(sy / 0.05))
            if not r.track_free(L, gy, gx, nid):
                ok = False
                print(f"stub {net} x={x} L{L}: blocked at y={sy:.2f}")
                break
        if not ok:
            continue
        t2 = pcbnew.PCB_TRACK(b)
        t2.SetStart(pcbnew.VECTOR2I(MM(x), MM(y0)))
        t2.SetEnd(pcbnew.VECTOR2I(MM(x), MM(y1)))
        t2.SetWidth(MM(0.10))
        t2.SetLayer(LAYERS[L])
        t2.SetNet(b.FindNet(net))
        b.Add(t2)
        r._stamp_track(L, (x, y0), (x, y1), nid)
        g = r.geom.setdefault(net, {"objects": [], "cells": set()})
        g["objects"].append(t2)
        print(f"stub {net} x={x} L{L}: drawn")
    r.rebuild_blockers()
    pcbnew.SaveBoard(PATH, b)
    for net in ROUTE_AFTER:
        if r.net_components(net) <= 1:
            print(f"{net}: connected by stub alone")
            continue
        if r.route_net(net, via_cost=2.0, max_exp=500000) and r.net_components(net) <= 1:
            pcbnew.SaveBoard(PATH, b)
            print(f"ROUTE {net}: OK ({time.time()-t0:.0f}s)", flush=True)
        else:
            if net in r.geom:
                # keep the stubs: rip only non-stub geometry is complex;
                # leave geometry as-is (route_net partials are committed
                # tracks; a later pass can continue from them)
                pass
            print(f"ROUTE {net}: FAIL ({time.time()-t0:.0f}s)", flush=True)
    pcbnew.SaveBoard(PATH, b)
    print("GATES DONE")

if __name__ == "__main__":
    main()
