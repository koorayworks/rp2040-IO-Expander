#!/usr/bin/env python3
"""VBUS final joins:
1) D1.5 (F, 6.4375,11.0) -> F track west -> via -> In2 track west into
   the In2 trunk at x=4.05. Via spot chosen from model-checked candidates.
2) J2 A9/B4 (11.45,0.725): 0.6mm-wide F track straight south to y=3.2
   (real clearances verified: NPTH hole edge 0.74mm away >= 0.525 needed,
   CC2 stub 0.35mm, GND pad 0.20mm), then a via to In2 and route_net
   for the remaining leg to the tree."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["vbusfix"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

def add_track(b, r, net, L, a, c, w=0.10):
    t2 = pcbnew.PCB_TRACK(b)
    t2.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
    t2.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    t2.SetWidth(MM(w))
    t2.SetLayer(LAYERS[L])
    t2.SetNet(b.FindNet(net))
    b.Add(t2)
    nid = r.net_ids[net]
    cells = r._stamp_track(L, a, c, nid)
    g = r.geom.setdefault(net, {"objects": [], "cells": set()})
    g["objects"].append(t2)
    g["cells"] |= cells
    return t2

def add_via(b, r, net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    v.SetWidth(MM(0.40))
    v.SetDrill(MM(0.20))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(b.FindNet(net))
    b.Add(v)
    nid = r.net_ids[net]
    cells = r._stamp_via(x, y, nid)
    g = r.geom.setdefault(net, {"objects": [], "cells": set()})
    g["objects"].append(v)
    g["cells"] |= cells
    return v

def leg_free(r, L, a, c, nid):
    steps = max(2, int(max(abs(c[0] - a[0]), abs(c[1] - a[1])) / 0.05))
    for i in range(steps + 1):
        tt = i / steps
        sx, sy = a[0] + (c[0] - a[0]) * tt, a[1] + (c[1] - a[1]) * tt
        gx, gy = int(round(sx / 0.05)), int(round(sy / 0.05))
        if not (0 <= gx < 361 and 0 <= gy < 871) or not r.track_free(L, gy, gx, nid):
            return False
    return True

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    net = "USB_VBUS"
    nid = r.net_ids[net]
    print("components before:", r.net_components(net), flush=True)
    # --- 1) D1.5 join ---
    done1 = False
    for (vx, vy) in [(5.35, 11.0), (5.5, 10.85), (5.2, 11.15), (5.6, 11.3), (5.05, 10.8)]:
        gx, gy = int(round(vx / 0.05)), int(round(vy / 0.05))
        if not r.via_free(gy, gx, nid):
            continue
        if not leg_free(r, 0, (6.4375, 11.0), (vx, vy), nid):
            continue
        if not leg_free(r, 1, (vx, vy), (4.05, vy), nid):
            continue
        add_track(b, r, net, 0, (6.4375, 11.0), (vx, vy))
        add_via(b, r, net, vx, vy)
        add_track(b, r, net, 1, (vx, vy), (4.05, vy))
        r.rebuild_blockers()
        print(f"D1.5 joined via ({vx},{vy})", flush=True)
        done1 = True
        break
    if not done1:
        print("D1.5 join: no via candidate worked", flush=True)
    # --- 2) A9/B4 join ---
    add_track(b, r, net, 0, (11.45, 0.9), (11.45, 3.2), w=0.60)
    r.rebuild_blockers()
    print("A9/B4 south track drawn; components:", r.net_components(net), flush=True)
    if r.net_components(net) > 1:
        ok = r.route_net(net, via_cost=2.0, max_exp=400000)
        print("route_net:", ok, "components:", r.net_components(net), flush=True)
    pcbnew.SaveBoard(PATH, b)
    print("VBUSFIX DONE", flush=True)

if __name__ == "__main__":
    main()
