#!/usr/bin/env python3
"""Route ONE net; if plain A* fails, grow short manual escape stubs from
its pads (model-checked) to move the seed region out of the sealed pad
field, then route again. Swap fallback last. Saves only on success.
Usage: stub.py NETNAME"""
import pcbnew, os, sys, time, math
import importlib.util

TARGET_NET = sys.argv[1] if len(sys.argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["stub"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

def main():
    name = TARGET_NET
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    if r.net_components(name) <= 1:
        print(f"{name}: already connected")
        return
    t0 = time.time()
    nid = r.net_ids[name]
    net_obj = b.FindNet(name)

    def try_route(exp=400000):
        return r.route_net(name, via_cost=2.0, max_exp=exp) and r.net_components(name) <= 1

    ok = try_route(300000)
    if not ok and name in r.geom:
        r.ripup(name)
    if not ok:
        pads = r.pad_groups[name]
        tried = 0
        for rec in pads:
            if ok or tried >= 10:
                break
            cx, cy = rec["cx"], rec["cy"]
            # outward direction from the module centre first (for U1 pads)
            dxm, dym = cx - 9.0, cy - 34.0
            if abs(dxm) >= abs(dym):
                first = (1 if dxm > 0 else -1, 0)
            else:
                first = (0, 1 if dym > 0 else -1)
            dirs = sorted(DIRS, key=lambda d: -(d[0] * first[0] + d[1] * first[1]))
            for L in sorted(rec["layers"]):
                if ok or tried >= 10:
                    break
                for (dx, dy) in dirs:
                    if ok or tried >= 10:
                        break
                    for ln in (2.0, 3.0, 1.2):
                        ex, ey = cx + dx * ln, cy + dy * ln
                        if not (0.3 <= ex <= 17.7 and 0.3 <= ey <= 43.2):
                            continue
                        steps = max(2, int(ln / 0.05))
                        good = True
                        for i in range(steps + 1):
                            tt = i / steps
                            sx, sy = cx + (ex - cx) * tt, cy + (ey - cy) * tt
                            gx, gy = int(round(sx / 0.05)), int(round(sy / 0.05))
                            if not (0 <= gx < 361 and 0 <= gy < 871) or not r.track_free(L, gy, gx, nid):
                                good = False
                                break
                        if not good:
                            continue
                        # endpoint openness: at least 5 of 8 neighbours free
                        gx, gy = int(round(ex / 0.05)), int(round(ey / 0.05))
                        free_n = 0
                        for ddy in (-1, 0, 1):
                            for ddx in (-1, 0, 1):
                                if ddx == 0 and ddy == 0:
                                    continue
                                if r.track_free(L, gy + ddy, gx + ddx, nid):
                                    free_n += 1
                        if free_n < 5:
                            continue
                        tried += 1
                        t2 = pcbnew.PCB_TRACK(b)
                        t2.SetStart(pcbnew.VECTOR2I(MM(cx), MM(cy)))
                        t2.SetEnd(pcbnew.VECTOR2I(MM(ex), MM(ey)))
                        t2.SetWidth(MM(0.10))
                        t2.SetLayer(LAYERS[L])
                        t2.SetNet(net_obj)
                        b.Add(t2)
                        r._stamp_track(L, (cx, cy), (ex, ey), nid)
                        g = r.geom.setdefault(name, {"objects": [], "cells": set()})
                        g["objects"].append(t2)
                        r.rebuild_blockers()
                        if try_route(300000):
                            ok = True
                            print(f"{name}: stub escape L{L} dir({dx},{dy}) len{ln} worked")
                        else:
                            b.Remove(t2)
                            g["objects"].remove(t2)
                            if name in r.geom:
                                r.ripup(name)
                            r.rebuild_copper()
                            r.rebuild_blockers()
                        break  # next direction after a drawn stub
    if not ok:
        blockers = rt.corridor_blockers(r, name, set())
        for blk in blockers[:2]:
            r.ripup(blk)
            if try_route(400000):
                if not (r.route_net(blk, via_cost=2.0, max_exp=300000) and r.net_components(blk) <= 1):
                    print(f"{name}: swap OK, sacrificed {blk}")
                ok = True
                break
            else:
                if name in r.geom:
                    r.ripup(name)
                r.route_net(blk, via_cost=2.0, max_exp=300000)
    if ok:
        pcbnew.SaveBoard(PATH, b)
        print(f"{name}: OK ({time.time()-t0:.0f}s)")
    else:
        print(f"{name}: FAIL ({time.time()-t0:.0f}s) -- board NOT saved")

if __name__ == "__main__":
    main()
