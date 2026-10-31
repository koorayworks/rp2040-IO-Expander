#!/usr/bin/env python3
"""Production repair driver (round 3).

Model: relaxed track clearance (nearest-obstacle dilation only; still
>=0.105mm real clearance for 0.10mm tracks) but STRICT via clearance
(router's original via_free, both dilations at VIA_R=0.305).
Swaps: on failure the blocker is restored from its original track objects
(never re-routed), so a failed swap leaves the board byte-identical for
that net. A blocker whose re-route fails after a successful swap is
queued and retried in later rounds.

Usage: python3 fix4.py NET [NET...]
"""
import pcbnew, os, sys, time
import importlib.util

ARGS = sys.argv[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fix1", os.path.join(HERE, "fix1.py"))
f1 = importlib.util.module_from_spec(spec)
sys.argv = ["fix4"]
spec.loader.exec_module(f1)
rt = f1.rt
PATH = f1.PATH
LAYERMAP = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}


def patch_track_relaxed(r):
    def tf(L, y, x, nid):
        if r.copper[L][y, x] == nid:
            return True
        if r.edge_block[y, x]:
            return False
        o1 = r.trk_o[L][0][y, x]
        return o1 == 0 or o1 == nid
    r.track_free = tf
    # via_free intentionally left as router's strict original


def restore(r, name, objects):
    nid = r.net_ids[name]
    g = {"objects": list(objects), "cells": set()}
    for t in objects:
        r.b.Add(t)
        if t.GetClass() == "PCB_VIA":
            pos = t.GetPosition()
            g["cells"] |= r._stamp_via(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), nid)
        else:
            L = LAYERMAP.get(t.GetLayer())
            if L is None:
                continue
            a = (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y))
            c = (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
            g["cells"] |= r._stamp_track(L, a, c, nid)
    r.geom[name] = g
    r.rebuild_blockers()


def route(r, name):
    return f1.route_fast(r, name, via_cost=1.5, w_h=2.0)


def try_net(r, name, unrouted):
    if r.net_components(name) <= 1:
        return True
    if route(r, name) and r.net_components(name) <= 1:
        return True
    if name in r.geom:
        r.ripup(name)
    blockers = rt.corridor_blockers(r, name, set())
    for blk in blockers[:8]:
        if blk not in r.geom:
            continue
        saved = list(r.geom[blk]["objects"])
        r.ripup(blk)
        if route(r, name) and r.net_components(name) <= 1:
            if route(r, blk) and r.net_components(blk) <= 1:
                print(f"    swap {blk}: both connected", flush=True)
            else:
                if blk in r.geom:
                    r.ripup(blk)
                print(f"    swap {blk}: {name} won, {blk} queued", flush=True)
                unrouted.add(blk)
            return True
        else:
            if name in r.geom:
                r.ripup(name)
            restore(r, blk, saved)
    return False


def main():
    targets = ARGS
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    patch_track_relaxed(r)
    unrouted = set()
    for n in list(r.pad_groups):
        if n != "GND" and r.net_components(n) > 1:
            unrouted.add(n)
    print("model-unrouted at start:", sorted(unrouted), flush=True)
    if not targets:
        targets = sorted(unrouted)
    t0 = time.time()
    for rnd in range(4):
        todo = [n for n in targets if n in unrouted]
        todo += [n for n in sorted(unrouted) if n not in todo]
        if not todo:
            break
        progress = False
        for name in todo:
            ts = time.time()
            got = try_net(r, name, unrouted)
            if got and r.net_components(name) <= 1:
                unrouted.discard(name)
                pcbnew.SaveBoard(PATH, b)
                progress = True
                print(f"[{rnd}] {name}: OK ({time.time()-ts:.0f}s) left={sorted(unrouted)}", flush=True)
            else:
                print(f"[{rnd}] {name}: FAIL ({time.time()-ts:.0f}s)", flush=True)
        if not progress:
            break
    print("FINAL model-unrouted:", sorted(unrouted), f"({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
