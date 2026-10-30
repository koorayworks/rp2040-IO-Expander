#!/usr/bin/env python3
"""D1.5 (USB_VBUS, F (6.4375,11.0)) -> join the VBUS tree's F.Cu segment
at (5.1,13.9)-(4.35,13.9) via a model-checked 2-segment F path, trying
several waypoints. Fallback: via down at a model-checked spot west of
D1, then In2 west into the trunk."""
import pcbnew, os, sys, math
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["d1fix"]
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
    steps = max(2, int(math.hypot(c[0] - a[0], c[1] - a[1]) / 0.05))
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
    src = (6.4375, 11.0)
    targets = [(5.1, 13.9), (4.7, 13.9), (4.35, 13.9)]
    waypoints = [(5.9, 12.3), (6.0, 12.8), (5.7, 12.0), (6.1, 12.5),
                 (5.8, 13.2), (6.2, 13.4), (5.5, 12.6)]
    done = False
    for tgt in targets:
        if done:
            break
        if leg_free(r, 0, src, tgt, nid):
            add_track(b, r, net, 0, src, tgt)
            print("direct F track to", tgt, flush=True)
            done = True
            break
        for wp in waypoints:
            if leg_free(r, 0, src, wp, nid) and leg_free(r, 0, wp, tgt, nid):
                add_track(b, r, net, 0, src, wp)
                add_track(b, r, net, 0, wp, tgt)
                print("F path via", wp, "to", tgt, flush=True)
                done = True
                break
    if not done:
        # via fallback: scan a wider grid west/southwest of D1.5
        for vx in [4.6 + 0.15 * i for i in range(12)]:
            if done:
                break
            for vy in [10.4 + 0.15 * j for j in range(12)]:
                gx, gy = int(round(vx / 0.05)), int(round(vy / 0.05))
                if not r.via_free(gy, gx, nid):
                    continue
                if not leg_free(r, 0, src, (vx, vy), nid):
                    continue
                if not leg_free(r, 1, (vx, vy), (4.05, vy), nid):
                    continue
                add_track(b, r, net, 0, src, (vx, vy))
                add_via(b, r, net, vx, vy)
                add_track(b, r, net, 1, (vx, vy), (4.05, vy))
                print(f"via fallback at ({vx:.2f},{vy:.2f})", flush=True)
                done = True
                break
    r.rebuild_blockers()
    print("components:", r.net_components(net), flush=True)
    pcbnew.SaveBoard(PATH, b)
    print("D1FIX DONE", flush=True)

if __name__ == "__main__":
    main()
