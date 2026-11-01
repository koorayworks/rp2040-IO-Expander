#!/usr/bin/env python3
"""Micro-router for the 4 nets the stock grid router cannot move:
PR1, 3V3_USB, 3V3 (mux hop), 3V3_BAT.

Same A* as router.py, but the obstacle model is rebuilt from EXACT sampled
copper (cell centers tested against true pad shapes / track capsules)
instead of bbox-stamped cells, and the dilation radii are set so the true
clearance stays >= 0.15mm for tracks (0.05 half-width + 0.10 clearance)
and >= 0.30mm for vias (0.20 radius + 0.10 clearance) after accounting for
the 0.05mm sampling pitch. KiCad DRC remains the final judge.
"""
import pcbnew, os, sys, math, time
import numpy as np
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["micro_route"]
spec.loader.exec_module(rt)

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board_revb")
PATH = os.path.join(BASE, "ext_board_revb.kicad_pcb")
MM = pcbnew.FromMM
TM = pcbnew.ToMM
CELL = rt.CELL
W, H, NL = rt.W, rt.H, rt.NL
LAYMAP = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}

rt.OFF_TRK = rt.offsets_within(0.155)
rt.OFF_VIA = rt.offsets_within(0.305)


def sample_copper(b, r):
    copper = [np.zeros((H, W), dtype=np.int32) for _ in range(NL)]
    # ---- pads (exact shape via HitTest over the bbox) ----
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            name = pad.GetNetname()
            nid = r.nid(name) if name else rt.OBST
            ls = pad.GetLayerSet()
            if pad.GetDrillSize().x > 0:
                layers = (0, 1, 2)
            else:
                layers = tuple(L for L in (0, 2) if ls.Contains((pcbnew.F_Cu, pcbnew.B_Cu)[L // 2]))
            if not layers:
                continue
            bb = pad.GetBoundingBox()
            x0, x1 = TM(bb.GetLeft()), TM(bb.GetRight())
            y0, y1 = TM(bb.GetTop()), TM(bb.GetBottom())
            ix0 = max(0, int(math.floor(x0 / CELL)) - 1); ix1 = min(W - 1, int(math.ceil(x1 / CELL)) + 1)
            iy0 = max(0, int(math.floor(y0 / CELL)) - 1); iy1 = min(H - 1, int(math.ceil(y1 / CELL)) + 1)
            for iy in range(iy0, iy1 + 1):
                for ix in range(ix0, ix1 + 1):
                    if pad.HitTest(pcbnew.VECTOR2I(MM(ix * CELL), MM(iy * CELL)), 0):
                        for L in layers:
                            copper[L][iy, ix] = nid
    # ---- tracks & vias ----
    for t in b.GetTracks():
        name = t.GetNetname()
        if not name:
            continue
        nid = r.nid(name)
        if t.GetClass() == "PCB_VIA":
            pos = t.GetPosition(); vx, vy = TM(pos.x), TM(pos.y)
            rad = TM(t.GetWidth()) / 2.0
            ix0 = max(0, int((vx - rad) / CELL) - 1); ix1 = min(W - 1, int((vx + rad) / CELL) + 1)
            iy0 = max(0, int((vy - rad) / CELL) - 1); iy1 = min(H - 1, int((vy + rad) / CELL) + 1)
            for iy in range(iy0, iy1 + 1):
                for ix in range(ix0, ix1 + 1):
                    if math.hypot(ix * CELL - vx, iy * CELL - vy) <= rad:
                        for L in range(NL):
                            copper[L][iy, ix] = nid
        else:
            L = LAYMAP.get(t.GetLayer())
            if L is None:
                continue
            a = t.GetStart(); c = t.GetEnd()
            ax, ay, cx, cy = TM(a.x), TM(a.y), TM(c.x), TM(c.y)
            hw = TM(t.GetWidth()) / 2.0
            ix0 = max(0, int((min(ax, cx) - hw) / CELL) - 1); ix1 = min(W - 1, int((max(ax, cx) + hw) / CELL) + 1)
            iy0 = max(0, int((min(ay, cy) - hw) / CELL) - 1); iy1 = min(H - 1, int((max(ay, cy) + hw) / CELL) + 1)
            dx, dy = cx - ax, cy - ay
            seg2 = dx * dx + dy * dy
            for iy in range(iy0, iy1 + 1):
                for ix in range(ix0, ix1 + 1):
                    px, py = ix * CELL, iy * CELL
                    if seg2 == 0:
                        dd = math.hypot(px - ax, py - ay)
                    else:
                        tt = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
                        dd = math.hypot(px - (ax + tt * dx), py - (ay + tt * dy))
                    if dd <= hw:
                        copper[L][iy, ix] = nid
    return copper


def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    t0 = time.time()
    r.copper = sample_copper(b, r)
    r.pads_copper = [c.copy() for c in r.copper]
    r.rebuild_blockers()
    print(f"sampled copper in {time.time()-t0:.0f}s", flush=True)
    for net in ("PR1", "3V3_USB", "3V3", "3V3_BAT"):
        print(f"{net}: components={r.net_components(net)}", flush=True)
    for net in ("PR1", "3V3_USB", "3V3", "3V3_BAT"):
        for vc in (2.0, 5.0, 1.2):
            if r.net_components(net) <= 1:
                break
            ok = r.route_net(net, via_cost=vc, max_exp=4000000)
            print(f"  {net} via_cost={vc}: ok={ok} components={r.net_components(net)} ({time.time()-t0:.0f}s)", flush=True)
            if r.net_components(net) <= 1:
                pcbnew.SaveBoard(PATH, b)
                break
        print(f"{net}: FINAL components={r.net_components(net)}", flush=True)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(PATH, b)
    print("MICRO ROUTE DONE", flush=True)


if __name__ == "__main__":
    main()
