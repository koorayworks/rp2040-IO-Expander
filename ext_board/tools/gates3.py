#!/usr/bin/env python3
"""J2 gate fix v3: the USB_VBUS F.Cu bus bar under the J2 pad row seals
every mid-row signal gate. Rip VBUS and D-_C, draw the six parallel
stubs, route the four signal nets, then re-route VBUS last (it has many
pads and can dive to inner/back layers and go around)."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["gates3"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

STUBS = [("CC1", 7.75), ("USB_D-_C", 8.25), ("USB_D+_C", 8.75),
         ("USB_D-_C", 9.25), ("USB_D+_C", 9.75), ("CC2", 10.75)]

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    for n in ("USB_VBUS", "USB_D-_C"):
        if n in r.geom:
            r.ripup(n)
            print("ripped", n, flush=True)
    r.rebuild_blockers()
    for (net, x) in STUBS:
        nid = r.net_ids[net]
        y0, y1 = 0.725, 3.4
        steps = int(abs(y1 - y0) / 0.05)
        blocked_at = None
        for i in range(steps + 1):
            sy = y0 + (y1 - y0) * (i / steps)
            gx, gy = int(round(x / 0.05)), int(round(sy / 0.05))
            if not r.track_free(0, gy, gx, nid):
                blocked_at = sy
                break
        if blocked_at is not None:
            print(f"stub {net} x={x}: BLOCKED at y={blocked_at:.2f}", flush=True)
            continue
        t2 = pcbnew.PCB_TRACK(b)
        t2.SetStart(pcbnew.VECTOR2I(MM(x), MM(y0)))
        t2.SetEnd(pcbnew.VECTOR2I(MM(x), MM(y1)))
        t2.SetWidth(MM(0.10))
        t2.SetLayer(pcbnew.F_Cu)
        t2.SetNet(b.FindNet(net))
        b.Add(t2)
        r._stamp_track(0, (x, y0), (x, y1), nid)
        g = r.geom.setdefault(net, {"objects": [], "cells": set()})
        g["objects"].append(t2)
        print(f"stub {net} x={x}: drawn", flush=True)
    r.rebuild_blockers()
    pcbnew.SaveBoard(PATH, b)
    for net in ("USB_D-_C", "USB_D+_C", "CC1", "CC2", "USB_VBUS"):
        if r.net_components(net) <= 1:
            print(f"{net}: connected already", flush=True)
            continue
        if r.route_net(net, via_cost=2.0, max_exp=700000) and r.net_components(net) <= 1:
            pcbnew.SaveBoard(PATH, b)
            print(f"ROUTE {net}: OK ({time.time()-t0:.0f}s)", flush=True)
        else:
            print(f"ROUTE {net}: FAIL ({time.time()-t0:.0f}s)", flush=True)
    pcbnew.SaveBoard(PATH, b)
    print("GATES3 DONE", flush=True)

if __name__ == "__main__":
    main()
