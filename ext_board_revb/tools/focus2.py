#!/usr/bin/env python3
"""Focused fine-grid boost-cluster search around U3 (10.0,29.2) r0.
Replicates the deterministic mux/divider/J7P commits from solve2, then scans
the boost cluster at 0.05/0.10mm steps (the global 0.3mm inner grid can miss
sub-0.3mm pockets between module fanout vias). Saves plan.json on success."""
import pcbnew, os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2

BASE = sp.BASE
d = s2.d

def main():
    b = pcbnew.LoadBoard(os.path.join(BASE, "ext_board_revb.kicad_pcb"))
    sp.do_surgery(b)
    obs, padrects_B = sp.load_obstacles(b)
    pl = sp.Placer(obs, padrects_B)
    plan = dict(parts={}, vias=[])
    # --- mux + divider (same deterministic result as solve2) ---
    s2.commit(pl, "mux", 1.5, 23.9, 270, s2.MUXNET, "U4")
    mc = s2.ctrs("mux", 1.5, 23.9, 270)
    gvia = pl.via_spot(mc["1"][0][0], mc["1"][0][1], 1.35)
    div = s2.try_divider(pl, mc)
    assert div is not None and gvia is not None, "mux/divider replication failed"
    plan["parts"]["U4"] = dict(fp="mux", x=1.5, y=23.9, rot=270)
    plan["vias"].append(dict(x=gvia[0], y=gvia[1], net="GND", for_="U4.1"))
    plan["parts"]["R4"] = dict(fp="r0603", **div["R4"])
    plan["parts"]["R5"] = dict(fp="r0603", **{k: div["R5"][k] for k in ("x", "y", "rot")})
    plan["vias"].append(dict(x=div["R5"]["via"][0], y=div["R5"]["via"][1], net="GND", for_="R5.2"))
    if div["C6"]:
        plan["parts"]["C6"] = dict(fp="c0603", **{k: div["C6"][k] for k in ("x", "y", "rot")})
        plan["vias"].append(dict(x=div["C6"]["via"][0], y=div["C6"]["via"][1], net="GND", for_="C6.2"))
    muxVIN2 = mc["6"][0]
    print(f"mux/divider replicated: R4 {div['R4']} R5 {div['R5']} C6 {div['C6']}", flush=True)
    # --- J7P (same as solve2) ---
    J7NET = {"1": "BAT_IN", "2": "GND"}
    pl.commit_part(s2.GEOM["j7p"]["pads"], 1.2, 28.7, 270, False, J7NET, None, "J7")
    plan["parts"]["J7"] = dict(fp="j7p", x=1.2, y=28.7, rot=270)
    j7c_ctrs = {}
    for (rr, n, ls, c) in sp.pad_world_rects(s2.GEOM["j7p"]["pads"], 1.2, 28.7, 270, False):
        j7c_ctrs.setdefault(n, []).append(c)
    # --- boost: fine scan ---
    U3NET = {"1": "GND", "2": "3V3_BAT", "3": "GND", "4": "VBAT", "5": "BOOST_SW", "6": "VBAT", "7": "GND"}
    u3s = []
    anchors = [(10.1, 31.5, 0), (9.3, 30.8, 90), (16.4, 27.0, 90), (16.4, 29.5, 270),
               (10.5, 34.3, 0), (1.6, 34.5, 0), (16.5, 31.0, 0), (10.0, 31.4, 180)]
    for (ax, ay, r) in anchors:
        cy = ay - 0.3
        while cy <= ay + 0.3:
            cx = ax - 0.3
            while cx <= ax + 0.3:
                ok, _, _ = s2.check(pl, "u3", round(cx, 2), round(cy, 2), r, U3NET, "U3")
                if ok:
                    spot = pl.via_spot(round(cx, 2), round(cy, 2), 0.16)
                    if spot is not None:
                        u3s.append((d((cx, cy), (ax, ay)), cx, cy, r, (spot[0], spot[1])))
                cx += 0.05
            cy += 0.05
    u3s.sort()
    print(f"focused U3 candidates: {len(u3s)}", flush=True)
    best = None
    for (_, ux, uy, ur, usp) in u3s[:40]:
        s0 = s2.snap(pl)
        s2.commit(pl, "u3", ux, uy, ur, U3NET, "U3")
        uc = s2.ctrs("u3", ux, uy, ur)
        cins = []
        for r in (0, 90, 180, 270):
            gx = -3.4
            while gx <= 3.4:
                gy = -3.4
                while gy <= 3.4:
                    cx2, cy2 = uc["6"][0][0] + gx, uc["6"][0][1] + gy
                    if d((cx2, cy2), uc["6"][0]) <= 3.4:
                        ok, _, _ = s2.check(pl, "c0603", cx2, cy2, r, {"1": "VBAT", "2": "GND"}, "C4")
                        if ok:
                            c = s2.ctrs("c0603", cx2, cy2, r)
                            vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.6, avoid=s2.own_rects("c0603", cx2, cy2, r))
                            cins.append((d(c["1"][0], uc["6"][0]) + (0.0 if vs else 1.5), cx2, cy2, r, vs))
                    gy += 0.1
                gx += 0.1
        cins.sort()
        l1s = []
        if cins:
            for r in (0, 90, 180, 270):
                gx = -5.0
                while gx <= 5.0:
                    gy = -5.0
                    while gy <= 5.0:
                        cx2, cy2 = ux + gx, uy + gy
                        if cy2 <= 34.2 and d((cx2, cy2), (ux, uy)) <= 5.0:
                            ok, _, _ = s2.check(pl, "l1", cx2, cy2, r, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
                            if ok and s2.part_max_y("l1", cx2, cy2, r) <= 35.4:
                                c = s2.ctrs("l1", cx2, cy2, r)
                                dd = d(c["1"][0], uc["5"][0])
                                if dd <= 3.8: l1s.append((dd, cx2, cy2, r))
                        gy += 0.1
                    gx += 0.1
            l1s.sort()
        for (_, lx, ly, lr) in l1s[:5]:
            s1 = s2.snap(pl)
            s2.commit(pl, "l1", lx, ly, lr, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
            lc = s2.ctrs("l1", lx, ly, lr)
            couts = []
            for r in (0, 90, 180, 270):
                gx = -3.8
                while gx <= 3.8:
                    gy = -3.8
                    while gy <= 3.8:
                        cx2, cy2 = uc["2"][0][0] + gx, uc["2"][0][1] + gy
                        if d((cx2, cy2), uc["2"][0]) <= 3.8:
                            ok, _, _ = s2.check(pl, "c0603", cx2, cy2, r, {"1": "3V3_BAT", "2": "GND"}, "C5")
                            if ok:
                                c = s2.ctrs("c0603", cx2, cy2, r)
                                if d(c["1"][0], lc["2"][0]) <= 3.4:
                                    vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.6, avoid=s2.own_rects("c0603", cx2, cy2, r))
                                    couts.append((d(c["1"][0], uc["2"][0]) + d(c["1"][0], lc["2"][0]) + (0.0 if vs else 1.5), cx2, cy2, r, vs))
                        gy += 0.1
                    gx += 0.1
            couts.sort()
            if cins and couts:
                score = (3.0 * d(lc["1"][0], uc["5"][0]) + 1.2 * cins[0][0] + 1.2 * couts[0][0]
                         + 0.30 * uy + 0.35 * ly + 0.30 * d(uc["6"][0], j7c_ctrs["1"][0])
                         + 0.30 * d(lc["2"][0], muxVIN2))
                if best is None or score < best[0]:
                    best = (score, dict(U3=(ux, uy, ur), U3EP=usp, L1=(lx, ly, lr),
                                        C4=(cins[0][1], cins[0][2], cins[0][3], cins[0][4]),
                                        C5=(couts[0][1], couts[0][2], couts[0][3], couts[0][4])))
                    print(f"FOCUS cluster score {score:.2f}: U3 ({ux:.2f},{uy:.2f}) r{ur} L1 ({lx:.2f},{ly:.2f}) r{lr} C4 ({cins[0][1]:.2f},{cins[0][2]:.2f}) C5 ({couts[0][1]:.2f},{couts[0][2]:.2f})", flush=True)
            s2.rollback(pl, s1)
        s2.rollback(pl, s0)
    if best is None:
        print("FOCUS BOOST FAILED"); return
    _, cl = best
    ux, uy, ur = cl["U3"]; s2.commit(pl, "u3", ux, uy, ur, U3NET, "U3")
    plan["parts"]["U3"] = dict(fp="u3", x=ux, y=uy, rot=ur)
    plan["vias"].append(dict(x=cl["U3EP"][0], y=cl["U3EP"][1], net="GND", for_="U3.EP"))
    lx, ly, lr = cl["L1"]; s2.commit(pl, "l1", lx, ly, lr, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
    plan["parts"]["L1"] = dict(fp="l1", x=lx, y=ly, rot=lr)
    c4x, c4y, c4r, c4v = cl["C4"]; s2.commit(pl, "c0603", c4x, c4y, c4r, {"1": "VBAT", "2": "GND"}, "C4")
    plan["parts"]["C4"] = dict(fp="c0603", x=c4x, y=c4y, rot=c4r)
    if c4v: plan["vias"].append(dict(x=c4v[0], y=c4v[1], net="GND", for_="C4.2"))
    c5x, c5y, c5r, c5v = cl["C5"]; s2.commit(pl, "c0603", c5x, c5y, c5r, {"1": "3V3_BAT", "2": "GND"}, "C5")
    plan["parts"]["C5"] = dict(fp="c0603", x=c5x, y=c5y, rot=c5r)
    if c5v: plan["vias"].append(dict(x=c5v[0], y=c5v[1], net="GND", for_="C5.2"))
    ucf = s2.ctrs("u3", ux, uy, ur)
    # --- SW1 (same logic as solve2) ---
    SWNET = {"1": "BAT_IN", "2": "VBAT", "3": None}
    swc = []
    tgt = j7c_ctrs["1"][0]
    for r in (0, 90, 180, 270):
        cy = 23.6
        while cy <= 36.0:
            cx = 0.9
            while cx <= 17.1:
                if d((cx, cy), tgt) > 11.0: cx += 0.1; continue
                ok, _, _ = s2.check(pl, "sw1", cx, cy, r, SWNET, "SW1")
                if ok:
                    c = s2.ctrs("sw1", cx, cy, r)
                    swc.append((d(c["1"][0], tgt) + 0.5 * d(c["2"][0], ucf["6"][0]) + 0.1 * cy, cx, cy, r))
                cx += 0.1
            cy += 0.1
    swc.sort()
    print(f"SW1 candidates: {len(swc)}", flush=True)
    if not swc: print("SW1 FAILED"); return
    _, sx, sy, sr = swc[0]
    s2.commit(pl, "sw1", sx, sy, sr, SWNET, "SW1")
    plan["parts"]["SW1"] = dict(fp="sw1", x=sx, y=sy, rot=sr)
    print(f"SW1 chosen ({sx:.2f},{sy:.2f}) rot{sr}", flush=True)
    # --- C7 optional ---
    c7best = None
    for r in (0, 90, 180, 270):
        for gx in range(-24, 25, 2):
            for gy in range(-24, 25, 2):
                cx2, cy2 = muxVIN2[0] + gx * 0.15, muxVIN2[1] + gy * 0.15
                if d((cx2, cy2), muxVIN2) > 3.6: continue
                ok, _, _ = s2.check(pl, "c0603", cx2, cy2, r, {"1": "3V3_BAT", "2": "GND"}, "C7")
                if not ok: continue
                c = s2.ctrs("c0603", cx2, cy2, r)
                vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.25, avoid=s2.own_rects("c0603", cx2, cy2, r))
                if vs is None: continue
                sc = d(c["1"][0], muxVIN2)
                if c7best is None or sc < c7best[0]: c7best = (sc, cx2, cy2, r, vs)
    if c7best:
        _, c7x, c7y, c7r, c7v = c7best
        plan["parts"]["C7"] = dict(fp="c0603", x=c7x, y=c7y, rot=c7r)
        plan["vias"].append(dict(x=c7v[0], y=c7v[1], net="GND", for_="C7.2"))
        print(f"C7 placed ({c7x:.1f},{c7y:.1f})", flush=True)
    json.dump(plan, open(os.path.join(BASE, "tools", "plan.json"), "w"), indent=1)
    print("FOCUS PLAN SAVED:", json.dumps(plan["parts"], indent=1))
    print("VIAS:", plan["vias"])

if __name__ == "__main__":
    main()
