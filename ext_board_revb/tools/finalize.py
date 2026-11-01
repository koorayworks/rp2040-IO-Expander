#!/usr/bin/env python3
"""Finalize REV.B plan.json with the probe-verified center-south boost cluster.

Mux/divider/J7P replicate the deterministic solve2 results. Boost cluster is
anchored on the probe data: U3 (10.1,31.5) r0 is the only U3 pocket in the
board center; its L1 must sit south (pads to y=36.6, 1.4mm clear of the
antenna keepout at y=38.0). East anchor's only L1 overhangs the board edge
(pad2 rect to x=18.30 > 18.0); west anchor's L1 lands inside the keepout.
"""
import pcbnew, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2

d = s2.d
check, commit, ctrs, snap, rollback = s2.check, s2.commit, s2.ctrs, s2.snap, s2.rollback

b = pcbnew.LoadBoard(os.path.join(sp.BASE, "ext_board_revb.kicad_pcb"))
sp.do_surgery(b)
obs, padrects_B = sp.load_obstacles(b)
pl = sp.Placer(obs, padrects_B)
plan = dict(parts={}, vias=[])

# ---- mux + divider (deterministic, as in solve2 runs) ----
commit(pl, "mux", 1.5, 23.9, 270, s2.MUXNET, "U4")
mc = ctrs("mux", 1.5, 23.9, 270)
gvia = pl.via_spot(mc["1"][0][0], mc["1"][0][1], 1.35)
assert gvia is not None, "mux GND via missing"
plan["parts"]["U4"] = dict(fp="mux", x=1.5, y=23.9, rot=270)
plan["vias"].append(dict(x=gvia[0], y=gvia[1], net="GND", for_="U4.1"))
div = s2.try_divider(pl, mc)
assert div is not None, "divider failed"
plan["parts"]["R4"] = dict(fp="r0603", **div["R4"])
plan["parts"]["R5"] = dict(fp="r0603", **{k: div["R5"][k] for k in ("x", "y", "rot")})
plan["vias"].append(dict(x=div["R5"]["via"][0], y=div["R5"]["via"][1], net="GND", for_="R5.2"))
assert div["C6"] is None, f"unexpected C6 {div['C6']}"
muxVIN2 = mc["6"][0]
print(f"mux/divider ok: R4 {div['R4']} R5 {div['R5']} gvia {gvia}", flush=True)

# ---- J7P (deterministic choice from solve2 scan) ----
J7NET = {"1": "BAT_IN", "2": "GND"}
pl.commit_part(s2.GEOM["j7p"]["pads"], 1.2, 28.7, 270, False, J7NET, None, "J7")
plan["parts"]["J7"] = dict(fp="j7p", x=1.2, y=28.7, rot=270)
j7c = {}
for (rr, n, ls, c) in sp.pad_world_rects(s2.GEOM["j7p"]["pads"], 1.2, 28.7, 270, False):
    j7c.setdefault(n, []).append(c)
print(f"J7P ok: pin1 {j7c['1'][0]} pin2 {j7c['2'][0]}", flush=True)

# ---- boost cluster: U3 anchor (10.1,31.5) r0 ----
U3NET = {"1": "GND", "2": "3V3_BAT", "3": "GND", "4": "VBAT", "5": "BOOST_SW", "6": "VBAT", "7": "GND"}
ux, uy, ur = 10.1, 31.5, 0
ok, worst, info = check(pl, "u3", ux, uy, ur, U3NET, "U3")
assert ok, f"U3 anchor invalid: {worst} {info}"
commit(pl, "u3", ux, uy, ur, U3NET, "U3")
usp = pl.via_spot(ux, uy, 0.16)
assert usp is not None, "U3 EP via missing"
plan["parts"]["U3"] = dict(fp="u3", x=ux, y=uy, rot=ur)
plan["vias"].append(dict(x=usp[0], y=usp[1], net="GND", for_="U3.EP"))
uc = ctrs("u3", ux, uy, ur)
print(f"U3 ok: pads { {k: v[0] for k, v in uc.items()} } EPvia {usp}", flush=True)

# ---- L1: fine scan south of U3, pads may reach y<=36.8 (keepout at 38.0) ----
l1s = []
for r in (270, 90, 0, 180):
    gx = 10.0
    while gx <= 12.2:
        gy = 33.6
        while gy <= 35.8:
            ok, _, _ = check(pl, "l1", round(gx, 2), round(gy, 2), r, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
            if ok:
                my = s2.part_max_y("l1", gx, gy, r)
                if my <= 36.8:
                    c = ctrs("l1", gx, gy, r)
                    dd = d(c["1"][0], uc["5"][0])
                    if dd <= 3.8: l1s.append((dd + 0.2 * my, round(gx, 2), round(gy, 2), r, round(my, 2), round(dd, 2)))
            gy += 0.05
        gx += 0.05
l1s.sort()
assert l1s, "no L1 near anchor"
_, lx, ly, lr, lmaxy, ldsw = l1s[0]
commit(pl, "l1", lx, ly, lr, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
plan["parts"]["L1"] = dict(fp="l1", x=lx, y=ly, rot=lr)
lc = ctrs("l1", lx, ly, lr)
print(f"L1 ok: ({lx},{ly}) r{lr} dSW {ldsw} maxy {lmaxy}", flush=True)

def cap_scan(ctr, rad, netmap, ref, extra=None, step=0.1):
    out = []
    gx = -rad
    while gx <= rad:
        gy = -rad
        while gy <= rad:
            cx2, cy2 = round(ctr[0] + gx, 2), round(ctr[1] + gy, 2)
            if d((cx2, cy2), ctr) <= rad:
                for r in (0, 90, 180, 270):
                    ok, _, _ = check(pl, "c0603", cx2, cy2, r, netmap, ref)
                    if ok:
                        c = ctrs("c0603", cx2, cy2, r)
                        vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.6, avoid=s2.own_rects("c0603", cx2, cy2, r))
                        out.append((cx2, cy2, r, c, vs))
                        break
            gy += step
        gx += step
    return out

# ---- C4 (CIN): near VIN pad ----
c4s = []
for (cx2, cy2, r, c, vs) in cap_scan(uc["6"][0], 4.5, {"1": "VBAT", "2": "GND"}, "C4"):
    c4s.append((d(c["1"][0], uc["6"][0]) + (0.0 if vs else 1.5) + 0.15 * cy2, cx2, cy2, r, vs))
c4s.sort()
assert c4s, "no CIN"
_, c4x, c4y, c4r, c4v = c4s[0]
commit(pl, "c0603", c4x, c4y, c4r, {"1": "VBAT", "2": "GND"}, "C4")
plan["parts"]["C4"] = dict(fp="c0603", x=c4x, y=c4y, rot=c4r)
if c4v: plan["vias"].append(dict(x=c4v[0], y=c4v[1], net="GND", for_="C4.2"))
print(f"C4 ok: ({c4x},{c4y}) r{c4r} via {c4v}", flush=True)

# ---- C5 (COUT): near VOUT pad and L1.2 ----
c5s = []
for (cx2, cy2, r, c, vs) in cap_scan(uc["2"][0], 4.5, {"1": "3V3_BAT", "2": "GND"}, "C5"):
    if d(c["1"][0], lc["2"][0]) > 4.5: continue
    c5s.append((d(c["1"][0], uc["2"][0]) + 0.7 * d(c["1"][0], lc["2"][0]) + (0.0 if vs else 1.5) + 0.15 * cy2, cx2, cy2, r, vs))
c5s.sort()
assert c5s, "no COUT"
_, c5x, c5y, c5r, c5v = c5s[0]
commit(pl, "c0603", c5x, c5y, c5r, {"1": "3V3_BAT", "2": "GND"}, "C5")
plan["parts"]["C5"] = dict(fp="c0603", x=c5x, y=c5y, rot=c5r)
if c5v: plan["vias"].append(dict(x=c5v[0], y=c5v[1], net="GND", for_="C5.2"))
print(f"C5 ok: ({c5x},{c5y}) r{c5r} via {c5v}", flush=True)

# ---- SW1 (same scoring as solve2; radius grows if needed) ----
SWNET = {"1": "BAT_IN", "2": "VBAT", "3": None}
tgt = j7c["1"][0]
swc = []
for rad in (11.0, 14.0):
    for r in (0, 90, 180, 270):
        cy = 23.6
        while cy <= 36.0:
            cx = 0.9
            while cx <= 17.1:
                if d((cx, cy), tgt) <= rad:
                    ok, _, _ = check(pl, "sw1", round(cx, 2), round(cy, 2), r, SWNET, "SW1")
                    if ok:
                        c = ctrs("sw1", round(cx, 2), round(cy, 2), r)
                        swc.append((d(c["1"][0], tgt) + 0.5 * d(c["2"][0], uc["6"][0]) + 0.1 * cy, round(cx, 2), round(cy, 2), r))
                cx += 0.1
            cy += 0.1
    if swc: break
swc.sort()
print(f"SW1 candidates: {len(swc)}", flush=True)
assert swc, "SW1 FAILED"
_, sx, sy, sr = swc[0]
commit(pl, "sw1", sx, sy, sr, SWNET, "SW1")
plan["parts"]["SW1"] = dict(fp="sw1", x=sx, y=sy, rot=sr)
print(f"SW1 ok: ({sx},{sy}) r{sr} pads { {k: v[0] for k, v in ctrs('sw1', sx, sy, sr).items()} }", flush=True)

# ---- C7 (optional, near mux VIN2) ----
c7s = []
for (cx2, cy2, r, c, vs) in cap_scan(muxVIN2, 3.2, {"1": "3V3_BAT", "2": "GND"}, "C7"):
    if vs is None: continue
    c7s.append((d(c["1"][0], muxVIN2), cx2, cy2, r, vs))
c7s.sort()
if c7s:
    _, c7x, c7y, c7r, c7v = c7s[0]
    commit(pl, "c0603", c7x, c7y, c7r, {"1": "3V3_BAT", "2": "GND"}, "C7")
    plan["parts"]["C7"] = dict(fp="c0603", x=c7x, y=c7y, rot=c7r)
    plan["vias"].append(dict(x=c7v[0], y=c7v[1], net="GND", for_="C7.2"))
    print(f"C7 ok: ({c7x},{c7y}) r{c7r} via {c7v}", flush=True)
else:
    print("C7 skipped (no spot with GND via near mux VIN2)", flush=True)

json.dump(plan, open(os.path.join(sp.BASE, "tools", "plan.json"), "w"), indent=1)
print("PLAN SAVED:", json.dumps(plan), flush=True)
