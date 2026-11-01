#!/usr/bin/env python3
"""REV.B mux re-placement search v6: precomputed R4/R5 fit sets,
filtered per mux candidate by rect clearance; real checks only for
shortlisted combos."""
import pcbnew, os, sys, math, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2

BASE = sp.BASE
t00 = time.time()
b = pcbnew.LoadBoard("/tmp/board_prebuild.kicad_pcb")
sp.do_surgery(b)
obs, padrects_B = sp.load_obstacles(b)
pl = sp.Placer(obs, padrects_B)

FIXED = [
    ("U3", "u3", 10.1, 31.5, 0, {"1": "GND", "2": "3V3_BAT", "3": "GND", "4": "VBAT", "5": "BOOST_SW", "6": "VBAT", "7": "GND"}),
    ("L1", "l1", 11.35, 34.85, 270, {"1": "BOOST_SW", "2": "3V3_BAT"}),
    ("C4", "c0603", 14.55, 30.05, 0, {"1": "VBAT", "2": "GND"}),
    ("C5", "c0603", 9.35, 34.3, 90, {"1": "3V3_BAT", "2": "GND"}),
    ("SW1", "sw1", 2.3, 34.8, 0, {"1": "BAT_IN", "2": "VBAT", "3": None}),
    ("J7", "j7p", 1.2, 28.7, 270, {"1": "BAT_IN", "2": "GND"}),
]
for ref, key, x, y, rot, nm in FIXED:
    ok, worst, info = s2.check(pl, key, x, y, rot, nm, ref)
    assert ok, (ref, worst, info)
    s2.commit(pl, key, x, y, rot, nm, ref)
print("fixed parts committed", flush=True)

R4NET = {"1": "3V3_USB", "2": "PR1"}
R5NET = {"1": "PR1", "2": "GND"}
U2PAD5 = (6.64, 20.50)
WEBVIA = (5.30, 25.62)
C51 = (9.35, 35.08)
CLR = 0.12

def d(a, bb): return math.hypot(a[0] - bb[0], a[1] - bb[1])

def scan_fits(key, netmap, ref, regions, rots, step=0.2):
    fits = []
    for (x0, x1, y0, y1) in regions:
        for rot in rots:
            cy = y0
            while cy <= y1 + 1e-9:
                cx = x0
                while cx <= x1 + 1e-9:
                    ok, worst, info = s2.check(pl, key, cx, cy, rot, netmap, ref)
                    if ok:
                        fits.append(dict(x=cx, y=cy, rot=rot,
                                         rects=s2.own_rects(key, cx, cy, rot),
                                         ctrs={k: v[0] for k, v in s2.ctrs(key, cx, cy, rot).items()}))
                    cx += step
                cy += step
    return fits

def clear_of(fit_rects, other_rects):
    for r in fit_rects:
        for o in other_rects:
            if sp.rect_dist(r, o) < CLR - 1e-9:
                return False
    return True

print("precomputing R4 fits...", flush=True)
R4FITS = scan_fits("r0603", R4NET, "R4", [(1.2, 4.6, 27.6, 31.6), (4.4, 6.4, 32.8, 36.2)], (0, 90, 180, 270))
print(f"R4 fits: {len(R4FITS)} ({time.time()-t00:.0f}s)", flush=True)
print("precomputing R5 fits...", flush=True)
R5FITS = scan_fits("r0603", R5NET, "R5", [(4.4, 8.6, 32.8, 36.4), (1.2, 4.4, 31.8, 36.4)], (0, 90, 180, 270))
print(f"R5 fits: {len(R5FITS)} ({time.time()-t00:.0f}s)", flush=True)

solutions = []
regions = [(2.85, 3.75, 29.6, 31.4)]
for (x0, x1, y0, y1) in regions:
    nmux = 0
    for rot in (0, 90, 180, 270):
        cy = y0
        while cy <= y1 + 1e-9:
            cx = x0
            while cx <= x1 + 1e-9:
                ok, worst, info = s2.check(pl, "mux", cx, cy, rot, s2.MUXNET, "U4")
                if ok:
                    nmux += 1
                    mux_rects = s2.own_rects("mux", cx, cy, rot)
                    mc = {k: v[0] for k, v in s2.ctrs("mux", cx, cy, rot).items()}
                    snap0 = s2.snap(pl)
                    s2.commit(pl, "mux", cx, cy, rot, s2.MUXNET, "U4")
                    gvia = pl.via_spot(mc["1"][0], mc["1"][1], 2.2)
                    if gvia:
                        r4cand = [f for f in R4FITS if clear_of(f["rects"], mux_rects)]
                        r4cand.sort(key=lambda f: d(mc["4"], f["ctrs"]["2"]) + 0.7 * d(f["ctrs"]["1"], mc["5"]))
                        for f4 in r4cand[:14]:
                            ok4, _, _ = s2.check(pl, "r0603", f4["x"], f4["y"], f4["rot"], R4NET, "R4")
                            if not ok4: continue
                            snap1 = s2.snap(pl)
                            s2.commit(pl, "r0603", f4["x"], f4["y"], f4["rot"], R4NET, "R4")
                            r5cand = [f for f in R5FITS if clear_of(f["rects"], mux_rects) and clear_of(f["rects"], f4["rects"])]
                            r5cand.sort(key=lambda f: d(mc["4"], f["ctrs"]["1"]))
                            for f5 in r5cand[:8]:
                                r5via = pl.via_spot(f5["ctrs"]["2"][0], f5["ctrs"]["2"][1], 1.6)
                                if not r5via: continue
                                ok5, _, _ = s2.check(pl, "r0603", f5["x"], f5["y"], f5["rot"], R5NET, "R5")
                                if not ok5: continue
                                score = (min(d(mc["3"], U2PAD5), d(mc["5"], U2PAD5))
                                         + 0.8 * min(d(mc["2"], WEBVIA), d(mc["7"], WEBVIA))
                                         + 0.8 * d(mc["6"], C51)
                                         + 0.6 * d(mc["4"], f4["ctrs"]["2"])
                                         + 0.6 * d(mc["4"], f5["ctrs"]["1"])
                                         + 0.4 * d(f4["ctrs"]["1"], mc["5"]))
                                solutions.append(dict(score=round(score, 2),
                                                      mux=(cx, cy, rot), r4=(f4["x"], f4["y"], f4["rot"]), r5=(f5["x"], f5["y"], f5["rot"]),
                                                      mux_gnd_via=gvia, r5_gnd_via=r5via, pads=mc))
                                break  # best R5 for this R4 is enough
                            s2.rollback(pl, snap1)
                    s2.rollback(pl, snap0)
                cx += 0.1
            cy += 0.1
    print(f"region ({x0},{y0}) done: mux fits {nmux}, solutions {len(solutions)}, {time.time()-t00:.0f}s", flush=True)

solutions.sort(key=lambda s: s["score"])
print(f"TOTAL solutions: {len(solutions)}")
for s in solutions[:10]:
    print(f"  score {s['score']}: mux={s['mux']} r4={s['r4']} r5={s['r5']} gvia={s['mux_gnd_via']} r5via={s['r5_gnd_via']}", flush=True)
json.dump(solutions[:20], open(os.path.join(BASE, "tools", "mux_regionA_cands.json"), "w"), indent=1)
print("wrote mux_regionA_cands.json", flush=True)
