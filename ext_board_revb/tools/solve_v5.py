#!/usr/bin/env python3
"""REV.B mux re-placement search v5 (lean): region A + C mux scan at
0.1mm, R4/R5 scans capped to nearest fits, progress to stdout."""
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
                    if ok: fits.append((cx, cy, rot))
                    cx += step
                cy += step
    return fits

solutions = []
regions = [(2.85, 3.75, 29.6, 31.4), (5.0, 6.2, 29.6, 31.4), (2.2, 3.6, 32.6, 34.2)]
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
                    snap0 = s2.snap(pl)
                    s2.commit(pl, "mux", cx, cy, rot, s2.MUXNET, "U4")
                    mc = s2.ctrs("mux", cx, cy, rot)
                    gvia = pl.via_spot(mc["1"][0][0], mc["1"][0][1], 2.2)
                    if gvia:
                        r4fits = scan_fits("r0603", R4NET, "R4",
                                           [(1.2, 4.6, 27.6, 31.6), (4.4, 6.4, 32.8, 36.2)], (0, 90, 180, 270))
                        r4scored = []
                        for f in r4fits:
                            c = s2.ctrs("r0603", f[0], f[1], f[2])
                            r4scored.append((d(mc["4"][0], c["2"][0]) + 0.7 * d(c["1"][0], mc["5"][0]), f))
                        r4scored.sort()
                        for (_, (r4x, r4y, r4r)) in r4scored[:30]:
                            snap1 = s2.snap(pl)
                            s2.commit(pl, "r0603", r4x, r4y, r4r, R4NET, "R4")
                            r4c = s2.ctrs("r0603", r4x, r4y, r4r)
                            r5fits = scan_fits("r0603", R5NET, "R5",
                                               [(4.4, 8.6, 32.8, 36.4), (1.2, 4.4, 31.8, 36.4)], (0, 90, 180, 270))
                            r5scored = []
                            for f in r5fits:
                                c = s2.ctrs("r0603", f[0], f[1], f[2])
                                r5scored.append((d(mc["4"][0], c["1"][0]), f))
                            r5scored.sort()
                            for (_, (r5x, r5y, r5r)) in r5scored[:12]:
                                r5c = s2.ctrs("r0603", r5x, r5y, r5r)
                                r5via = pl.via_spot(r5c["2"][0][0], r5c["2"][0][1], 1.6)
                                if not r5via: continue
                                score = (min(d(mc["3"][0], U2PAD5), d(mc["5"][0], U2PAD5))
                                         + 0.8 * min(d(mc["2"][0], WEBVIA), d(mc["7"][0], WEBVIA))
                                         + 0.8 * d(mc["6"][0], C51)
                                         + 0.6 * d(mc["4"][0], r4c["2"][0])
                                         + 0.6 * d(mc["4"][0], r5c["1"][0])
                                         + 0.4 * d(r4c["1"][0], mc["5"][0]))
                                solutions.append(dict(score=round(score, 2),
                                                      mux=(cx, cy, rot), r4=(r4x, r4y, r4r), r5=(r5x, r5y, r5r),
                                                      mux_gnd_via=gvia, r5_gnd_via=r5via,
                                                      pads={k: v[0] for k, v in mc.items()}))
                            s2.rollback(pl, snap1)
                    s2.rollback(pl, snap0)
                cx += 0.1
            cy += 0.1
    print(f"region ({x0},{y0}) done: mux fits {nmux}, solutions {len(solutions)}, {time.time()-t00:.0f}s", flush=True)

solutions.sort(key=lambda s: s["score"])
print(f"TOTAL solutions: {len(solutions)}")
for s in solutions[:10]:
    print(f"  score {s['score']}: mux={s['mux']} r4={s['r4']} r5={s['r5']} gvia={s['mux_gnd_via']} r5via={s['r5_gnd_via']}", flush=True)
json.dump(solutions[:20], open(os.path.join(BASE, "tools", "mux_v4_cands.json"), "w"), indent=1)
print("wrote mux_v4_cands.json", flush=True)
