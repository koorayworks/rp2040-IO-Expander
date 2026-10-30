#!/usr/bin/env python3
"""VBUS joins v2:
1) Delete the 0.6mm VBUS track at x=11.45 (shorts CC2's detour).
2) Rip CC2. Draw VBUS F track x=11.30 (0.10 wide) from the pad south to
   y=3.3 (clears the NPTH keep-out circle r=0.525 by ~0.215mm), via to
   In2, route_net to merge with the tree.
3) Redraw CC2's gate stub (x=10.75) and re-route CC2.
4) D1.5: probe a grid of via candidates west of D1.5; first fully
   model-checked via + legs wins."""
import pcbnew, os, sys, time, math
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["vbusfix2"]
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
    # 1) delete the wide track (F track of VBUS starting at (11.45,0.9))
    for t in list(b.GetTracks()):
        if t.GetNetname() == net and t.GetClass() != "PCB_VIA":
            s = t.GetStart()
            if abs(pcbnew.ToMM(s.x) - 11.45) < 0.01 and abs(pcbnew.ToMM(s.y) - 0.9) < 0.01:
                b.Remove(t)
                g = r.geom.get(net)
                if g:
                    g["objects"] = [o for o in g["objects"] if o is not t]
                print("removed wide VBUS track", flush=True)
    r.rebuild_copper()
    r.rebuild_blockers()
    # 2) rip CC2
    if "CC2" in r.geom:
        r.ripup("CC2")
        print("ripped CC2", flush=True)
    # 3) VBUS thin track + via + route
    add_track(b, r, net, 0, (11.30, 0.9), (11.30, 3.3))
    gx, gy = int(round(11.30 / 0.05)), int(round(3.3 / 0.05))
    if r.via_free(gy, gx, nid):
        add_via(b, r, net, 11.30, 3.3)
        print("VBUS via at (11.30,3.3)", flush=True)
    else:
        print("VBUS via spot blocked -- relying on route_net", flush=True)
    r.rebuild_blockers()
    ok = r.route_net(net, via_cost=2.0, max_exp=400000)
    print("VBUS route_net:", ok, "components:", r.net_components(net), flush=True)
    pcbnew.SaveBoard(PATH, b)
    # 4) CC2 stub + route
    nid2 = r.net_ids["CC2"]
    if leg_free(r, 0, (10.75, 0.725), (10.75, 3.4), nid2):
        add_track(b, r, "CC2", 0, (10.75, 0.725), (10.75, 3.4))
        r.rebuild_blockers()
        print("CC2 stub redrawn", flush=True)
    ok2 = r.route_net("CC2", via_cost=2.0, max_exp=500000)
    print("CC2 route_net:", ok2, "components:", r.net_components("CC2"), flush=True)
    pcbnew.SaveBoard(PATH, b)
    # 5) D1.5 via probe
    if r.net_components(net) > 1:
        done = False
        cands = []
        for vx in [5.0 + 0.15 * i for i in range(9)]:
            for vy in [10.55 + 0.15 * j for j in range(7)]:
                cands.append((vx, vy))
        for (vx, vy) in cands:
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
            print(f"D1.5 joined via ({vx:.2f},{vy:.2f}); components:", r.net_components(net), flush=True)
            done = True
            break
        if not done:
            print("D1.5: still no via candidate", flush=True)
        pcbnew.SaveBoard(PATH, b)
    print("VBUSFIX2 DONE", flush=True)

if __name__ == "__main__":
    main()
