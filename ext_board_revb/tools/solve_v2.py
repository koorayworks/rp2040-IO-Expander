#!/usr/bin/env python3
"""REV.B plan v2: relocate the mux+divider into the center-south basin.

The NW-corner mux placement is unroutable (PR1 pin is sealed in by the
JLEG bottom-row pads, the GPIO28 B.Cu wall and the mux's own pad field;
proven by both the stock grid router and the exact-geometry micro router).
This scan runs against the CURRENT board (surgery applied, REV.B parts
placed, VBAT/BAT_IN/BOOST_SW routed) minus the old mux parts, whose pads
sit outside the scan region.
"""
import pcbnew, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2

d = s2.d
check, commit, ctrs, snap, rollback = s2.check, s2.commit, s2.ctrs, s2.snap, s2.rollback

b = pcbnew.LoadBoard(os.path.join(sp.BASE, "ext_board_revb.kicad_pcb"))
obs, padrects_B = sp.load_obstacles(b)
pl = sp.Placer(obs, padrects_B)

U2PAD5 = (6.64, 20.50)
WEB = [(7.09, 24.90), (5.30, 25.62)]
C51 = (9.35, 35.08)

cands = []
for rot in (0, 90, 180, 270):
    cy = 26.5
    while cy <= 35.5:
        cx = 4.0
        while cx <= 10.0:
            ok, _, _ = check(pl, "mux", round(cx, 2), round(cy, 2), rot, s2.MUXNET, "U4")
            if ok:
                c = ctrs("mux", round(cx, 2), round(cy, 2), rot)
                vout = min(d(c["2"][0], w) for w in WEB)
                vout = min(vout, min(d(c["7"][0], w) for w in WEB))
                s = (1.0 * vout + 0.8 * d(c["3"][0], U2PAD5)
                     + 1.0 * d(c["6"][0], C51) + 0.02 * cy)
                cands.append((s, round(cx, 2), round(cy, 2), rot))
            cx += 0.1
        cy += 0.1
cands.sort()
print(f"mux v2 candidates: {len(cands)}", flush=True)
for c in cands[:5]:
    print(f"  score {c[0]:.2f} at ({c[1]},{c[2]}) r{c[3]}", flush=True)

chosen = None
alts = []
for (s, cx, cy, rot) in cands[:40]:
    s0 = snap(pl)
    commit(pl, "mux", cx, cy, rot, s2.MUXNET, "U4")
    mc = ctrs("mux", cx, cy, rot)
    gvia = pl.via_spot(mc["1"][0][0], mc["1"][0][1], 1.35)
    if gvia is None:
        rollback(pl, s0); continue
    div = s2.try_divider(pl, mc)
    if div is None:
        rollback(pl, s0); continue
    entry = dict(score=s, x=cx, y=cy, rot=rot,
                 R4=div["R4"], R5={k: div["R5"][k] for k in ("x", "y", "rot")},
                 R5via=div["R5"]["via"], C6=div["C6"], gvia=gvia,
                 pads={k: v[0] for k, v in mc.items()})
    alts.append(entry)
    print(f"feasible: ({cx},{cy}) r{rot} score {s:.2f} R4 ({div['R4']['x']},{div['R4']['y']}) r{div['R4']['rot']} "
          f"R5 ({div['R5']['x']},{div['R5']['y']}) r{div['R5']['rot']} C6 {div['C6']} gvia {gvia}", flush=True)
    if chosen is None:
        chosen = entry
    if len(alts) >= 4:
        break
    rollback(pl, s0)
assert chosen is not None, "no feasible mux v2 candidate"
json.dump(alts, open(os.path.join(sp.BASE, "tools", "mux_alts.json"), "w"), indent=1, default=str)
print("ALTS SAVED:", len(alts), flush=True)
