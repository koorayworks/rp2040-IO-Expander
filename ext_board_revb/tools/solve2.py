#!/usr/bin/env python3
"""REV.B placement search phase 2: mux+divider, J7, SW1, boost cluster."""
import pcbnew, os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp

BASE = sp.BASE
LDIR = "/usr/share/kicad/footprints"
FPDEF = {
    "mux":  (os.path.join(BASE, "revb.pretty"), "TPS2116DRLR", (-0.95, -1.20, 0.95, 1.20)),
    "u3":   (f"{LDIR}/Package_DFN_QFN.pretty", "DFN-6-1EP_2x2mm_P0.65mm_EP1x1.6mm", (-1.10, -1.10, 1.10, 1.10)),
    "l1":   (f"{LDIR}/Inductor_SMD.pretty", "L_1008_2520Metric", (-1.35, -1.15, 1.35, 1.15)),
    "c0603": (f"{LDIR}/Capacitor_SMD.pretty", "C_0603_1608Metric", (-0.90, -0.50, 0.90, 0.50)),
    "r0603": (f"{LDIR}/Resistor_SMD.pretty", "R_0603_1608Metric", (-0.90, -0.50, 0.90, 0.50)),
    "j7":   (f"{LDIR}/Connector_JST.pretty", "JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical", (-4.085, -4.36, 4.085, 0.75)),
    "j7s":  (f"{LDIR}/Connector_JST.pretty", "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", None),
    "sw1":  (f"{LDIR}/Button_Switch_SMD.pretty", "Nidec_Copal_CAS-120A", (-1.75, -2.90, 1.75, 2.65)),
}
GEOM = {}
for k, (lib, name, body) in FPDEF.items():
    pads, fab, crt = sp.parse_fp(os.path.join(lib, name + ".kicad_mod"))
    if body is None: body = fab if fab else crt
    GEOM[k] = dict(pads=pads, body=body, lib=lib, name=name)

def own_rects(key, cx, cy, rot):
    return [r for (r, num, layers, ctr) in sp.pad_world_rects(GEOM[key]["pads"], cx, cy, rot, True)]

def part_max_y(key, cx, cy, rot):
    ys = [r[3] for r in own_rects(key, cx, cy, rot)]
    br = sp.rect_xform(GEOM[key]["body"], rot, True)
    ys.append(br[3] + cy)
    return max(ys)

GEOM["j7p"] = dict(pads=[
    dict(num="1", type="thru_hole", x=0.0, y=0.0, rot=0, w=1.7, h=1.7, layers='"*.Cu" "*.Mask"', drill=0.9),
    dict(num="2", type="thru_hole", x=2.54, y=0.0, rot=0, w=1.7, h=1.7, layers='"*.Cu" "*.Mask"', drill=0.9)],
    body=None, lib=None, name="THT_PADS_2x_2.54mm")

def ctrs(key, cx, cy, rot, flip=True):
    out = {}
    for (r, num, layers, ctr) in sp.pad_world_rects(GEOM[key]["pads"], cx, cy, rot, flip):
        out.setdefault(num, []).append(ctr)
    return out

def check(pl, key, cx, cy, rot, netmap, ref):
    return pl.check_part(GEOM[key]["pads"], cx, cy, rot, True, netmap, GEOM[key]["body"], ref)

def commit(pl, key, cx, cy, rot, netmap, ref):
    pl.commit_part(GEOM[key]["pads"], cx, cy, rot, True, netmap, GEOM[key]["body"], ref)

def rollback(pl, snap):
    del pl.placed[snap[0]:]; del pl.bodies[snap[1]:]

def snap(pl): return (len(pl.placed), len(pl.bodies))

def d(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

MUXNET = {"1": "GND", "2": "3V3", "3": "3V3_USB", "4": "PR1", "5": "3V3_USB", "6": "3V3_BAT", "7": "3V3", "8": None}
U2PAD5 = (6.64, 20.50)
STUB_MID = (7.00, 20.50)

def scan_mux(pl):
    cands = []
    for rot in (0, 90, 180, 270):
        cy = 15.6
        while cy <= 26.8:
            cx = 0.8
            while cx <= 17.2:
                ok, worst, info = check(pl, "mux", cx, cy, rot, MUXNET, "U4")
                if ok:
                    c = ctrs("mux", cx, cy, rot)
                    s = (d(c["3"][0], U2PAD5) + d(c["5"][0], U2PAD5) * 0.5
                         + min(d(c["2"][0], STUB_MID), d(c["7"][0], STUB_MID))
                         + 0.45 * d(c["6"][0], (10.5, 29.5))
                         + (10.0 if cy > 23.4 else 0.0))
                    cands.append((s, cx, cy, rot))
                cx += 0.1
            cy += 0.1
    cands.sort()
    return cands

def try_divider(pl, mc):
    """mc = mux ctrs. Returns dict with R4/R5/(C6) placements or None."""
    P = mc["4"][0]; V1 = mc["3"][0]
    r4s = []
    for rot in (0, 90, 180, 270):
        for gx in range(-34, 35, 2):
            for gy in range(-34, 35, 2):
                cx, cy = P[0] + gx * 0.15, P[1] + gy * 0.15
                if d((cx, cy), P) > 5.2: continue
                ok, _, _ = check(pl, "r0603", cx, cy, rot, {"1": "3V3_USB", "2": "PR1"}, "R4")
                if ok:
                    c = ctrs("r0603", cx, cy, rot)
                    r4s.append((d(c["2"][0], P) + 0.4 * d(c["1"][0], V1), cx, cy, rot))
    r4s.sort()
    for (_, r4x, r4y, r4r) in r4s[:6]:
        s0 = snap(pl)
        commit(pl, "r0603", r4x, r4y, r4r, {"1": "3V3_USB", "2": "PR1"}, "R4")
        r4c = ctrs("r0603", r4x, r4y, r4r)
        r5s = []
        for rot in (0, 90, 180, 270):
            for gx in range(-34, 35, 2):
                for gy in range(-34, 35, 2):
                    cx, cy = P[0] + gx * 0.15, P[1] + gy * 0.15
                    if d((cx, cy), P) > 5.2: continue
                    ok, _, _ = check(pl, "r0603", cx, cy, rot, {"1": "PR1", "2": "GND"}, "R5")
                    if not ok: continue
                    c = ctrs("r0603", cx, cy, rot)
                    vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.25, avoid=own_rects("r0603", cx, cy, rot))
                    if vs is None: continue
                    r5s.append((d(c["1"][0], P) + 0.5 * d(c["1"][0], r4c["2"][0]), cx, cy, rot, vs))
        if r5s:
            r5s.sort()
            _, r5x, r5y, r5r, r5via = r5s[0]
            commit(pl, "r0603", r5x, r5y, r5r, {"1": "PR1", "2": "GND"}, "R5")
            # optional C6 near VIN1
            c6best = None
            for rot in (0, 90, 180, 270):
                for gx in range(-24, 25, 2):
                    for gy in range(-24, 25, 2):
                        cx, cy = V1[0] + gx * 0.15, V1[1] + gy * 0.15
                        if d((cx, cy), V1) > 3.6: continue
                        ok, _, _ = check(pl, "c0603", cx, cy, rot, {"1": "3V3_USB", "2": "GND"}, "C6")
                        if not ok: continue
                        c = ctrs("c0603", cx, cy, rot)
                        vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.25, avoid=own_rects("c0603", cx, cy, rot))
                        if vs is None: continue
                        sc = d(c["1"][0], V1)
                        if c6best is None or sc < c6best[0]: c6best = (sc, cx, cy, rot, vs)
            c6 = None
            if c6best:
                _, c6x, c6y, c6r, c6via = c6best
                commit(pl, "c0603", c6x, c6y, c6r, {"1": "3V3_USB", "2": "GND"}, "C6")
                c6 = dict(x=c6x, y=c6y, rot=c6r, via=c6via)
            return dict(R4=dict(x=r4x, y=r4y, rot=r4r), R5=dict(x=r5x, y=r5y, rot=r5r, via=r5s[0][4]), C6=c6)
        rollback(pl, s0)
    return None

def main():
    b = pcbnew.LoadBoard(os.path.join(BASE, "ext_board_revb.kicad_pcb"))
    sp.do_surgery(b)
    obs, padrects_B = sp.load_obstacles(b)
    pl = sp.Placer(obs, padrects_B)
    plan = dict(parts={}, vias=[])

    # ---- mux + divider ----
    cands = scan_mux(pl)
    print(f"mux candidates: {len(cands)}", flush=True)
    for label, pred in (("west band", lambda c: c[1] < 6), ("center band", lambda c: 6 <= c[1] <= 12), ("east band", lambda c: c[1] > 12)):
        sub = [c for c in cands if pred(c)]
        if sub: print(f"  best {label}: score {sub[0][0]:.2f} at ({sub[0][1]:.1f},{sub[0][2]:.1f}) r{sub[0][3]}", flush=True)
    chosen = None
    for (s, cx, cy, rot) in cands[:60]:
        s0 = snap(pl)
        commit(pl, "mux", cx, cy, rot, MUXNET, "U4")
        mc = ctrs("mux", cx, cy, rot)
        gvia = pl.via_spot(mc["1"][0][0], mc["1"][0][1], 1.35)
        if gvia is None:
            rollback(pl, s0); continue
        div = try_divider(pl, mc)
        if div is None:
            rollback(pl, s0); continue
        chosen = (cx, cy, rot, mc, div, gvia)
        print(f"MUX chosen ({cx:.2f},{cy:.2f}) rot{rot} score {s:.2f} GNDvia {gvia}", flush=True)
        print(f"  divider: R4 ({div['R4']['x']:.2f},{div['R4']['y']:.2f}) r{div['R4']['rot']}  R5 ({div['R5']['x']:.2f},{div['R5']['y']:.2f}) r{div['R5']['rot']}  C6 {div['C6']}", flush=True)
        print(f"  mux pads: " + ", ".join(f"{k}={v[0]}" for k, v in sorted(mc.items())), flush=True)
        break
    if not chosen:
        print("MUX FAILED"); return
    cx, cy, rot, mc, div, gvia = chosen
    plan["parts"]["U4"] = dict(fp="mux", x=cx, y=cy, rot=rot)
    plan["vias"].append(dict(x=gvia[0], y=gvia[1], net="GND", for_="U4.1"))
    plan["parts"]["R4"] = dict(fp="r0603", **div["R4"])
    plan["parts"]["R5"] = dict(fp="r0603", **{k: div["R5"][k] for k in ("x", "y", "rot")})
    plan["vias"].append(dict(x=div["R5"]["via"][0], y=div["R5"]["via"][1], net="GND", for_="R5.2"))
    if div["C6"]:
        plan["parts"]["C6"] = dict(fp="c0603", **{k: div["C6"][k] for k in ("x", "y", "rot")})
        plan["vias"].append(dict(x=div["C6"]["via"][0], y=div["C6"]["via"][1], net="GND", for_="C6.2"))
    muxVIN2 = mc["6"][0]

    # ---- J7: JST PH does not fit (proven by full-margin scan, best 0.106mm and
    # that spot violates the antenna keepout). Fallback per spec: THT pads only.
    GEOM["j7p"] = dict(pads=[
        dict(num="1", type="thru_hole", x=0.0, y=0.0, rot=0, w=1.7, h=1.7, layers='"*.Cu" "*.Mask"', drill=0.9),
        dict(num="2", type="thru_hole", x=2.54, y=0.0, rot=0, w=1.7, h=1.7, layers='"*.Cu" "*.Mask"', drill=0.9)],
        body=None, lib=None, name="THT_PADS_2x_2.54mm")
    J7NET = {"1": "BAT_IN", "2": "GND"}
    j7c = []
    for r in (0, 90, 180, 270):
        cy = 23.8
        while cy <= 36.4:
            cx = 0.9
            while cx <= 16.6:
                ok, worst, _ = pl.check_part(GEOM["j7p"]["pads"], cx, cy, r, False, J7NET, None, "J7", full=False)
                if ok:
                    # F-side annulus must stay out of the module can footprint
                    rects = own_rects("j7p", cx, cy, r) if False else [rr for (rr, n, ls, c) in sp.pad_world_rects(GEOM["j7p"]["pads"], cx, cy, r, False)]
                    if all(sp.rect_dist(rr, sp.CAN_F) >= 0.10 for rr in rects):
                        mid = ((rects[0][0] + rects[1][2]) / 2, (rects[0][1] + rects[1][3]) / 2)
                        j7c.append((0.6 * cy + 0.4 * d(mid, (12.5, 30.0)), cx, cy, r))
                cx += 0.1
            cy += 0.1
    j7c.sort()
    print(f"J7P candidates: {len(j7c)}", flush=True)
    if not j7c: print("J7P FAILED"); return
    _, jx, jy, jr = j7c[0]
    jkey = "j7p"
    pl.commit_part(GEOM["j7p"]["pads"], jx, jy, jr, False, J7NET, None, "J7")
    plan["parts"]["J7"] = dict(fp="j7p", x=jx, y=jy, rot=jr)
    j7c_ctrs = {}
    for (rr, n, ls, c) in sp.pad_world_rects(GEOM["j7p"]["pads"], jx, jy, jr, False):
        j7c_ctrs.setdefault(n, []).append(c)
    print(f"J7P chosen ({jx:.2f},{jy:.2f}) rot{jr} pin1 {j7c_ctrs['1'][0]} pin2 {j7c_ctrs['2'][0]}", flush=True)

    # ---- boost cluster (before SW1 so the switch fits around it) ----
    U3NET = {"1": "GND", "2": "3V3_BAT", "3": "GND", "4": "VBAT", "5": "BOOST_SW", "6": "VBAT", "7": "GND"}
    u3c = []
    for r in (0, 90, 180, 270):
        cy = 23.9
        while cy <= 35.6:
            cx = 0.9
            while cx <= 17.1:
                ok, _, _ = check(pl, "u3", cx, cy, r, U3NET, "U3")
                if ok:
                    spot = pl.via_spot(cx, cy, 0.16)
                    if spot is not None:
                        u3c.append((cy + 0.5 * d((cx, cy), (13.0, 29.0)), cx, cy, r, (spot[0], spot[1])))
                cx += 0.1
            cy += 0.1
    u3c.sort()
    print(f"U3 candidates: {len(u3c)}", flush=True)
    best = None
    tried = []
    for (_, ux, uy, ur, usp) in u3c:
        if any(d((ux, uy), t) < 1.2 for t in tried): continue
        tried.append((ux, uy))
        if len(tried) > 80: break
        s0 = snap(pl)
        commit(pl, "u3", ux, uy, ur, U3NET, "U3")
        uc = ctrs("u3", ux, uy, ur)
        # CIN scan (independent of L1; once per U3)
        cins = []
        for r in (0, 90, 180, 270):
            for gx in range(-22, 23, 2):
                for gy in range(-22, 23, 2):
                    cx2, cy2 = uc["6"][0][0] + gx * 0.15, uc["6"][0][1] + gy * 0.15
                    if d((cx2, cy2), uc["6"][0]) > 3.4: continue
                    ok, _, _ = check(pl, "c0603", cx2, cy2, r, {"1": "VBAT", "2": "GND"}, "C4")
                    if not ok: continue
                    c = ctrs("c0603", cx2, cy2, r)
                    vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.6, avoid=own_rects("c0603", cx2, cy2, r))
                    cins.append((d(c["1"][0], uc["6"][0]) + (0.0 if vs else 1.5), cx2, cy2, r, vs))
        cins.sort()
        if not cins:
            rollback(pl, s0); continue
        # L1 scan (inductor must stay north: center y <= 34.2, pads max y <= 35.4)
        l1s = []
        for r in (0, 90, 180, 270):
            for gx in range(-30, 31, 2):
                for gy in range(-30, 31, 2):
                    cx2, cy2 = ux + gx * 0.15, uy + gy * 0.15
                    if cy2 > 34.2: continue
                    if d((cx2, cy2), (ux, uy)) > 5.0: continue
                    ok, _, _ = check(pl, "l1", cx2, cy2, r, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
                    if not ok: continue
                    if part_max_y("l1", cx2, cy2, r) > 35.4: continue
                    c = ctrs("l1", cx2, cy2, r)
                    dd = d(c["1"][0], uc["5"][0])
                    if dd <= 3.8: l1s.append((dd, cx2, cy2, r))
        l1s.sort()
        for (_, lx, ly, lr) in l1s[:4]:
            s1 = snap(pl)
            commit(pl, "l1", lx, ly, lr, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
            lc = ctrs("l1", lx, ly, lr)
            # COUT near VOUT pad and L1 out
            couts = []
            for r in (0, 90, 180, 270):
                for gx in range(-25, 26, 2):
                    for gy in range(-25, 26, 2):
                        cx2, cy2 = uc["2"][0][0] + gx * 0.15, uc["2"][0][1] + gy * 0.15
                        if d((cx2, cy2), uc["2"][0]) > 3.8: continue
                        ok, _, _ = check(pl, "c0603", cx2, cy2, r, {"1": "3V3_BAT", "2": "GND"}, "C5")
                        if not ok: continue
                        c = ctrs("c0603", cx2, cy2, r)
                        if d(c["1"][0], lc["2"][0]) > 3.4: continue
                        vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.6, avoid=own_rects("c0603", cx2, cy2, r))
                        couts.append((d(c["1"][0], uc["2"][0]) + d(c["1"][0], lc["2"][0]) + (0.0 if vs else 1.5), cx2, cy2, r, vs))
            couts.sort()
            if len(tried) <= 3:
                print(f"  U3 try ({ux:.1f},{uy:.1f}) r{ur} L1 ({lx:.1f},{ly:.1f}): L1opts {len(l1s)}, CIN {len(cins)}, COUT {len(couts)}", flush=True)
            if cins and couts:
                score = (3.0 * d(lc["1"][0], uc["5"][0]) + 1.2 * cins[0][0] + 1.2 * couts[0][0]
                         + 0.30 * uy + 0.35 * ly + 0.30 * d(uc["6"][0], j7c_ctrs["1"][0])
                         + 0.30 * d(lc["2"][0], muxVIN2))
                if best is None or score < best[0]:
                    best = (score, dict(U3=(ux, uy, ur), U3EP=usp, L1=(lx, ly, lr),
                                        C4=(cins[0][1], cins[0][2], cins[0][3], cins[0][4]),
                                        C5=(couts[0][1], couts[0][2], couts[0][3], couts[0][4])))
                    print(f"cluster score {score:.2f}: U3 ({ux:.1f},{uy:.1f}) r{ur} L1 ({lx:.1f},{ly:.1f}) r{lr}", flush=True)
            rollback(pl, s1)
        rollback(pl, s0)
    if best is None:
        print("BOOST CLUSTER FAILED"); return
    _, cl = best
    ux, uy, ur = cl["U3"]; commit(pl, "u3", ux, uy, ur, U3NET, "U3")
    plan["parts"]["U3"] = dict(fp="u3", x=ux, y=uy, rot=ur)
    plan["vias"].append(dict(x=cl["U3EP"][0], y=cl["U3EP"][1], net="GND", for_="U3.EP"))
    lx, ly, lr = cl["L1"]; commit(pl, "l1", lx, ly, lr, {"1": "BOOST_SW", "2": "3V3_BAT"}, "L1")
    plan["parts"]["L1"] = dict(fp="l1", x=lx, y=ly, rot=lr)
    c4x, c4y, c4r, c4v = cl["C4"]; commit(pl, "c0603", c4x, c4y, c4r, {"1": "VBAT", "2": "GND"}, "C4")
    plan["parts"]["C4"] = dict(fp="c0603", x=c4x, y=c4y, rot=c4r)
    if c4v: plan["vias"].append(dict(x=c4v[0], y=c4v[1], net="GND", for_="C4.2"))
    c5x, c5y, c5r, c5v = cl["C5"]; commit(pl, "c0603", c5x, c5y, c5r, {"1": "3V3_BAT", "2": "GND"}, "C5")
    plan["parts"]["C5"] = dict(fp="c0603", x=c5x, y=c5y, rot=c5r)
    if c5v: plan["vias"].append(dict(x=c5v[0], y=c5v[1], net="GND", for_="C5.2"))
    ucf = ctrs("u3", ux, uy, ur)

    # ---- SW1 (fits around boost; VBAT leg scored against real U3 VIN pad) ----
    SWNET = {"1": "BAT_IN", "2": "VBAT", "3": None}
    swc = []
    tgt = j7c_ctrs["1"][0]
    for r in (0, 90, 180, 270):
        cy = 23.6
        while cy <= 36.0:
            cx = 0.9
            while cx <= 17.1:
                if d((cx, cy), tgt) > 11.0: cx += 0.1; continue
                ok, _, _ = check(pl, "sw1", cx, cy, r, SWNET, "SW1")
                if ok:
                    c = ctrs("sw1", cx, cy, r)
                    swc.append((d(c["1"][0], tgt) + 0.5 * d(c["2"][0], ucf["6"][0]) + 0.1 * cy, cx, cy, r))
                cx += 0.1
            cy += 0.1
    swc.sort()
    print(f"SW1 candidates: {len(swc)}", flush=True)
    if not swc: print("SW1 FAILED"); return
    _, sx, sy, sr = swc[0]
    commit(pl, "sw1", sx, sy, sr, SWNET, "SW1")
    plan["parts"]["SW1"] = dict(fp="sw1", x=sx, y=sy, rot=sr)
    swc_ctrs = ctrs("sw1", sx, sy, sr)
    print(f"SW1 chosen ({sx:.2f},{sy:.2f}) rot{sr} common {swc_ctrs['2'][0]}", flush=True)

    # ---- optional C7 near mux VIN2 ----
    c7best = None
    for r in (0, 90, 180, 270):
        for gx in range(-24, 25, 2):
            for gy in range(-24, 25, 2):
                cx2, cy2 = muxVIN2[0] + gx * 0.15, muxVIN2[1] + gy * 0.15
                if d((cx2, cy2), muxVIN2) > 3.6: continue
                ok, _, _ = check(pl, "c0603", cx2, cy2, r, {"1": "3V3_BAT", "2": "GND"}, "C7")
                if not ok: continue
                c = ctrs("c0603", cx2, cy2, r)
                vs = pl.via_spot(c["2"][0][0], c["2"][0][1], 1.25, avoid=own_rects("c0603", cx2, cy2, r))
                if vs is None: continue
                sc = d(c["1"][0], muxVIN2)
                if c7best is None or sc < c7best[0]: c7best = (sc, cx2, cy2, r, vs)
    if c7best:
        _, c7x, c7y, c7r, c7v = c7best
        plan["parts"]["C7"] = dict(fp="c0603", x=c7x, y=c7y, rot=c7r)
        plan["vias"].append(dict(x=c7v[0], y=c7v[1], net="GND", for_="C7.2"))
        print(f"C7 placed ({c7x:.1f},{c7y:.1f})", flush=True)
    else:
        print("C7 skipped (no clean spot)", flush=True)

    json.dump(plan, open(os.path.join(BASE, "tools", "plan.json"), "w"), indent=1)
    print("PLAN SAVED:", json.dumps(plan["parts"], indent=1))
    print("VIAS:", plan["vias"])

if __name__ == "__main__":
    main()
