#!/usr/bin/env python3
"""Round 5 build: apply one r5_solutions.json solution to a board copy,
refill zones, run kicad-cli DRC, and audit footprints vs the start snapshot.

Usage:
  python3 r5_build.py <sol_index> <out_dir>     # trial build into out_dir
  python3 r5_build.py <sol_index> APPLY         # build onto the real board file

Pass criteria (same as the round brief):
  - DRC errors == 0
  - warnings per type <= start baseline {copper_edge_clearance 34,
    silk_edge_clearance 2, silk_over_copper 11, silk_overlap 14, text_height 9},
    no new warning types
  - unconnected == 5, all zone<->zone pairs (no Pad/Track items)
  - audit: every footprint except C1 identical (pos/rot/flipped/pad nets+pos);
    C1 pad nets per pad number unchanged.
"""
import pcbnew, os, sys, json, math, shutil, subprocess, collections

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.dirname(HERE)
START = os.path.join(HERE, "board_step_r5_start.kicad_pcb")
REAL = os.path.join(EXT, "ext_board.kicad_pcb")
PRO = os.path.join(EXT, "ext_board.kicad_pro")
MM = pcbnew.FromMM
BASE_WARN = {"copper_edge_clearance": 34, "silk_edge_clearance": 2,
             "silk_over_copper": 11, "silk_overlap": 14, "text_height": 9}
OLD_STUBS = [((12.625, 19.90), (12.218, 19.493)), ((12.218, 19.493), (11.871, 19.493))]
CFGS = {
    "EW1W": ((-0.775, 0.0), (0.775, 0.0)),
    "EW1E": ((0.775, 0.0), (-0.775, 0.0)),
    "NS1N": ((0.0, -0.775), (0.0, 0.775)),
    "NS1S": ((0.0, 0.775), (0.0, -0.775)),
}


def close(a, b, tol=0.01):
    return abs(a - b) <= tol


def simplify(pts):
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        d1 = (round(pts[i][0] - pts[i - 1][0], 6), round(pts[i][1] - pts[i - 1][1], 6))
        d2 = (round(pts[i + 1][0] - pts[i][0], 6), round(pts[i + 1][1] - pts[i][1], 6))
        # collinear if direction vectors are positive scalar multiples
        cross = d1[0] * d2[1] - d1[1] * d2[0]
        dot = d1[0] * d2[0] + d1[1] * d2[1]
        if abs(cross) > 1e-9 or dot <= 0:
            out.append(pts[i])
    out.append(pts[-1])
    return out


def add_track(b, net, layer, a, c, w=0.10):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    t.SetWidth(MM(w))
    t.SetLayer(layer)
    t.SetNet(net)
    b.Add(t)
    return t


def set_c1_transform(b, sol):
    """Move/rotate C1 so its pads land on the solution's pad centres.
    Brute-forces the footprint orientation (flipped parts mirror), verifying
    resulting pad world positions against the CFGS target offsets."""
    c1 = b.FindFootprintByReference("C1")
    cx, cy = sol["cx"], sol["cy"]
    o1, o2 = CFGS[sol["cfg"]]
    want = {"1": (cx + o1[0], cy + o1[1]), "2": (cx + o2[0], cy + o2[1])}
    for ang in (0, 90, 180, 270):
        c1.SetPosition(pcbnew.VECTOR2I(MM(cx), MM(cy)))
        c1.SetOrientationDegrees(ang)
        got = {}
        for pad in c1.Pads():
            pp = pad.GetPosition()
            got[pad.GetNumber()] = (pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y))
        if all(close(got[k][0], want[k][0], 0.005) and close(got[k][1], want[k][1], 0.005) for k in want):
            return ang, got
    raise RuntimeError(f"no orientation reproduces pads for {sol['cfg']}: want {want}")


def build(sol, out_path):
    # Load from the output path itself (pre-populated with the start board):
    # KiCad resolves design rules from the sibling .kicad_pro, so loading the
    # tools/ snapshot directly would substitute default project settings and
    # SaveBoard would then write those defaults back out (observed in trial 0).
    b = pcbnew.LoadBoard(out_path)
    moved = not (sol["cfg"] == "EW1W" and sol["dx"] == 0 and sol["dy"] == 0)
    if moved:
        ang, got = set_c1_transform(b, sol)
        print(f"C1 moved to ({sol['cx']}, {sol['cy']}) cfg={sol['cfg']} orientation={ang} pads={got}")
        # delete old VBUS B stubs (collect first, then remove)
        tracks = list(b.GetTracks())
        n_rm = 0
        for t in tracks:
            if t.GetClass() == "PCB_VIA" or t.GetLayer() != pcbnew.B_Cu or t.GetNetname() != "USB_VBUS":
                continue
            s = (pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y))
            e = (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
            for (a, c) in OLD_STUBS:
                if (close(s[0], a[0]) and close(s[1], a[1]) and close(e[0], c[0]) and close(e[1], c[1])) or \
                   (close(s[0], c[0]) and close(s[1], c[1]) and close(e[0], a[0]) and close(e[1], a[1])):
                    b.Remove(t)
                    n_rm += 1
                    break
        assert n_rm == 2, f"removed {n_rm} old VBUS stubs"
        vbus_net = b.FindNet("USB_VBUS")
        o1, _ = CFGS[sol["cfg"]]
        p1c = (sol["cx"] + o1[0], sol["cy"] + o1[1])
        pts = simplify([p1c] + [tuple(p) for p in sol["vbus_path"]])
        for a, c in zip(pts, pts[1:]):
            if a != c:
                add_track(b, vbus_net, pcbnew.B_Cu, a, c)
    # GND via + stub (all solutions)
    gnd_net = b.FindNet("GND")
    vx, vy = sol["via"]
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy)))
    v.SetWidth(MM(0.40))
    v.SetDrill(MM(0.20))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(gnd_net)
    b.Add(v)
    _, o2 = CFGS[sol["cfg"]]
    p2c = (sol["cx"] + o2[0], sol["cy"] + o2[1])
    pts = simplify([p2c] + [tuple(p) for p in sol["gnd_path"]] + [(vx, vy)])
    for a, c in zip(pts, pts[1:]):
        if a != c:
            add_track(b, gnd_net, pcbnew.B_Cu, a, c)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(out_path, b)
    print("saved:", out_path)


def run_drc(board_path, tag):
    out = f"/tmp/drc_r5_{tag}.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--format", "json", "-o", out, board_path],
                   capture_output=True)
    return json.load(open(out))


def evaluate(d):
    errs = [v for v in d["violations"] if v["severity"] == "error"]
    warns = collections.Counter(v["type"] for v in d["violations"] if v["severity"] == "warning")
    unc = d.get("unconnected_items", [])
    unc_bad = []
    for u in unc:
        for it in u["items"]:
            if "Zone" not in it["description"]:
                unc_bad.append(it["description"])
    ok = (len(errs) == 0 and len(unc) == 5 and not unc_bad
          and all(warns.get(k, 0) <= v for k, v in BASE_WARN.items())
          and all(k in BASE_WARN for k in warns))
    print(f"DRC: errors={len(errs)} warnings={dict(warns)} unconnected={len(unc)} nonzone_unc={unc_bad}")
    for e in errs[:10]:
        print("  ERR:", e["type"], e.get("items"))
    return ok


def audit(board_path):
    start = json.load(open(os.path.join(HERE, "r5_start_audit.json")))
    b = pcbnew.LoadBoard(board_path)
    problems = []
    seen = set()
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        seen.add(ref)
        s = start[ref]
        p = fp.GetPosition()
        pos = [round(pcbnew.ToMM(p.x), 4), round(pcbnew.ToMM(p.y), 4)]
        rot = round(fp.GetOrientationDegrees(), 3)
        pads = sorted([[pad.GetNumber(), pad.GetNetname(),
                        round(pcbnew.ToMM(pad.GetPosition().x), 4),
                        round(pcbnew.ToMM(pad.GetPosition().y), 4)] for pad in fp.Pads()])
        if ref == "C1":
            if [pp[:2] for pp in pads] != [pp[:2] for pp in s["pads"]]:
                problems.append(f"C1 pad nets changed: {pads} vs {s['pads']}")
            continue
        if pos != s["pos"] or rot != s["rot"] or bool(fp.IsFlipped()) != s["flipped"] or pads != s["pads"]:
            problems.append(f"{ref}: pos {pos} vs {s['pos']}, rot {rot} vs {s['rot']}, pads differ={pads != s['pads']}")
    missing = set(start) - seen
    if missing:
        problems.append(f"missing footprints: {missing}")
    print("AUDIT:", "OK (only C1 may differ; it doesn't in pos/rot unless moved)" if not problems else problems)
    return not problems


def main():
    idx = int(sys.argv[1])
    mode = sys.argv[2]
    sols = json.load(open(os.path.join(HERE, "r5_solutions.json")))
    sol = sols[idx]
    print("solution:", sol["cfg"], "d=", (sol["dx"], sol["dy"]), "via=", sol["via"])
    if mode == "APPLY":
        # safety: the real board must still be byte-identical to the start snapshot
        import hashlib
        h = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
        assert h(REAL) == h(START), "real board differs from r5 start snapshot; aborting APPLY"
        out_path = REAL
    else:
        os.makedirs(mode, exist_ok=True)
        out_path = os.path.join(mode, "ext_board.kicad_pcb")
        shutil.copy(PRO, os.path.join(mode, "ext_board.kicad_pro"))
        shutil.copy(START, out_path)
    build(sol, out_path)
    d = run_drc(out_path, "apply" if mode == "APPLY" else f"cand{idx}")
    ok_drc = evaluate(d)
    ok_audit = audit(out_path)
    print("VERDICT:", "PASS" if (ok_drc and ok_audit) else "FAIL")
    return 0 if (ok_drc and ok_audit) else 1


if __name__ == "__main__":
    sys.exit(main())
