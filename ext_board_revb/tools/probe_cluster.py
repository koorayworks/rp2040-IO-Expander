import pcbnew, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2
d = s2.d
b = pcbnew.LoadBoard(os.path.join(sp.BASE, "ext_board_revb.kicad_pcb"))
sp.do_surgery(b)
obs, padrects_B = sp.load_obstacles(b)
pl = sp.Placer(obs, padrects_B)
s2.commit(pl, "mux", 1.5, 23.9, 270, s2.MUXNET, "U4")
mc = s2.ctrs("mux", 1.5, 23.9, 270)
div = s2.try_divider(pl, mc)
pl.commit_part(s2.GEOM["j7p"]["pads"], 1.2, 28.7, 270, False, {"1": "BAT_IN", "2": "GND"}, None, "J7")
U3NET = {"1": "GND", "2": "3V3_BAT", "3": "GND", "4": "VBAT", "5": "BOOST_SW", "6": "VBAT", "7": "GND"}
ux, uy, ur = 10.1, 31.5, 0
ok, worst, info = s2.check(pl, "u3", ux, uy, ur, U3NET, "U3")
print("U3 anchor ok:", ok, round(worst, 3), info, flush=True)
s2.commit(pl, "u3", ux, uy, ur, U3NET, "U3")
uc = s2.ctrs("u3", ux, uy, ur)
print("U3 pads:", {k: v[0] for k, v in uc.items()}, flush=True)

def capscan(ctr, netmap, ref, rad, step=0.1):
    out = []
    gx = -rad
    while gx <= rad:
        gy = -rad
        while gy <= rad:
            cx2, cy2 = round(ctr[0] + gx, 2), round(ctr[1] + gy, 2)
            if d((cx2, cy2), ctr) <= rad:
                for r in (0, 90, 180, 270):
                    ok2, _, _ = s2.check(pl, "c0603", cx2, cy2, r, netmap, ref)
                    if ok2:
                        c = s2.ctrs("c0603", cx2, cy2, r)
                        out.append((cx2, cy2, r, c))
                        break
            gy += step
        gx += step
    return out

cin34 = capscan(uc["6"][0], {"1": "VBAT", "2": "GND"}, "C4", 3.4)
print("CIN within 3.4 of VIN:", len(cin34), [(c[0], c[1], c[2]) for c in cin34[:6]], flush=True)
l1s = []
for r in (0, 90, 180, 270):
    gx = -5.0
    while gx <= 5.0:
        gy = -5.0
        while gy <= 5.0:
            cx2, cy2 = round(ux + gx, 2), round(uy + gy, 2)
            if d((cx2, cy2), (ux, uy)) <= 5.0:
                ok2, _, _ = s2.check(pl, "l1", cx2, cy2, r, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
                if ok2:
                    c = s2.ctrs("l1", cx2, cy2, r)
                    dd = d(c["1"][0], uc["5"][0])
                    if dd <= 3.8: l1s.append((round(dd, 2), cx2, cy2, r, round(s2.part_max_y("l1", cx2, cy2, r), 2)))
            gy += 0.1
        gx += 0.1
l1s.sort()
print("L1 options (dSW, x, y, rot, maxy):", l1s[:12], flush=True)
# COUT per top L1 (two radius settings)
for (dd, lx, ly, lr, my) in l1s[:3]:
    s1 = s2.snap(pl)
    s2.commit(pl, "l1", lx, ly, lr, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
    lc = s2.ctrs("l1", lx, ly, lr)
    co = []
    gx = -5.0
    while gx <= 5.0:
        gy = -5.0
        while gy <= 5.0:
            cx2, cy2 = round(uc["2"][0][0] + gx, 2), round(uc["2"][0][1] + gy, 2)
            if d((cx2, cy2), uc["2"][0]) <= 5.0:
                for r in (0, 90, 180, 270):
                    ok2, _, _ = s2.check(pl, "c0603", cx2, cy2, r, {"1": "3V3_BAT", "2": "GND"}, "C5")
                    if ok2:
                        c = s2.ctrs("c0603", cx2, cy2, r)
                        if d(c["1"][0], lc["2"][0]) <= 5.0:
                            co.append((round(d(c["1"][0], uc["2"][0]), 2), round(d(c["1"][0], lc["2"][0]), 2), cx2, cy2, r))
                        break
            gy += 0.1
        gx += 0.1
    co.sort()
    print(f"COUT for L1 ({lx},{ly}) r{lr}: {len(co)} options, best (dVOUT, dL1out, x, y, rot):", co[:5], flush=True)
    s2.rollback(pl, s1)
print("PROBE DONE", flush=True)
