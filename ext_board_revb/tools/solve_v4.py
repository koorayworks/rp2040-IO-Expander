#!/usr/bin/env python3
"""REV.B mux re-placement search v4.

Fixed: surgery + boost cluster + SW1 + J7P (plan v2 positions).
Scan: mux in candidate regions/rotations; for each fit, place R4/R5
(local scans) + GND vias; score by connection distances; emit top
candidates as JSON plans compatible with build.py.
"""
import pcbnew, os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2

BASE = sp.BASE
b = pcbnew.LoadBoard("/tmp/board_prebuild.kicad_pcb")
sp.do_surgery(b)
obs, padrects_B = sp.load_obstacles(b)
pl = sp.Placer(obs, padrects_B)

FIXED = [  # (ref, key, x, y, rot, netmap)
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
print("fixed parts committed")

R4NET = {"1": "3V3_USB", "2": "PR1"}
R5NET = {"1": "PR1", "2": "GND"}
U2PAD5 = (6.64, 20.50)
WEBVIA = (5.30, 25.62)     # existing 3V3 via (web entry)
C51 = (9.35, 35.08)

def d(a, bb): return math.hypot(a[0] - bb[0], a[1] - bb[1])

def try_r(pl, key, netmap, ref, regions, rots):
    """regions: list of (x0,x1,y0,y1); returns list of (score-dist-to-target...) raw fits"""
    fits = []
    for (x0, x1, y0, y1) in regions:
        for rot in rots:
            cy = y0
            while cy <= y1:
                cx = x0
                while cx <= x1:
                    ok, worst, info = s2.check(pl, key, cx, cy, rot, netmap, ref)
                    if ok:
                        fits.append((cx, cy, rot))
                    cx += 0.1
                cy += 0.1
    return fits

solutions = []
mux_regions = [
    # region A: east of J7, north of SW1
    (2.85, 3.75, 29.6, 31.4),
    # region B: south-west low (may clash SW1; cheap to test)
    (2.2, 3.6, 32.6, 34.2),
    # region C: current spot, rotated 90/270 included in rots
    (5.0, 6.2, 29.6, 31.4),
]
for (x0, x1, y0, y1) in mux_regions:
    for rot in (0, 90, 180, 270):
        cy = y0
        while cy <= y1:
            cx = x0
            while cx <= x1:
                ok, worst, info = s2.check(pl, "mux", cx, cy, rot, s2.MUXNET, "U4")
                if ok:
                    snap0 = s2.snap(pl)
                    s2.commit(pl, "mux", cx, cy, rot, s2.MUXNET, "U4")
                    mc = s2.ctrs("mux", cx, cy, rot)
                    # mux GND via
                    gvia = pl.via_spot(mc["1"][0][0], mc["1"][0][1], 2.2)
                    if gvia:
                        # R4 scan: west/south-west of board + near mux
                        r4fits = try_r(pl, "r0603", R4NET, "R4",
                                       [(1.2, 4.6, 27.6, 31.6), (4.4, 6.4, 32.8, 36.2)], (0, 90, 180, 270))
                        for (r4x, r4y, r4r) in r4fits[:400]:
                            snap1 = s2.snap(pl)
                            s2.commit(pl, "r0603", r4x, r4y, r4r, R4NET, "R4")
                            r4c = s2.ctrs("r0603", r4x, r4y, r4r)
                            r5fits = try_r(pl, "r0603", R5NET, "R5",
                                           [(4.4, 8.6, 32.8, 36.4), (1.2, 4.4, 31.8, 36.4)], (0, 90, 180, 270))
                            for (r5x, r5y, r5r) in r5fits[:200]:
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
    print(f"region done, solutions so far: {len(solutions)}", flush=True)

solutions.sort(key=lambda s: s["score"])
print(f"TOTAL solutions: {len(solutions)}")
for s in solutions[:10]:
    print(f"  score {s['score']}: mux={s['mux']} r4={s['r4']} r5={s['r5']} gvia={s['mux_gnd_via']} r5via={s['r5_gnd_via']}")
json.dump(solutions[:20], open(os.path.join(BASE, "tools", "mux_v4_cands.json"), "w"), indent=1)
print("wrote mux_v4_cands.json")
