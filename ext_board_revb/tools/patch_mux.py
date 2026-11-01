#!/usr/bin/env python3
"""Replace the unroutable NW mux cluster with a mux_alts.json candidate.

Usage: patch_mux.py [alt_index]   (default 0)
Removes U4/R4/R5 footprints and their build.py GND vias/link tracks,
places the candidate parts with the same pad verification as build.py.
"""
import pcbnew, os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2
import build as bl

BASE = sp.BASE
MM = pcbnew.FromMM; TM = pcbnew.ToMM
BOARD_PATH = os.path.join(BASE, "ext_board_revb.kicad_pcb")
idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
alt = json.load(open(os.path.join(BASE, "tools", "mux_alts.json")))[idx]
print(f"candidate {idx}: mux ({alt['x']},{alt['y']}) r{alt['rot']} score {alt['score']:.2f}")

parts = {"U4": dict(fp="mux", x=alt["x"], y=alt["y"], rot=alt["rot"]),
         "R4": dict(fp="r0603", x=alt["R4"]["x"], y=alt["R4"]["y"], rot=alt["R4"]["rot"]),
         "R5": dict(fp="r0603", x=alt["R5"]["x"], y=alt["R5"]["y"], rot=alt["R5"]["rot"])}
vias = [dict(x=alt["gvia"][0], y=alt["gvia"][1], net="GND", for_="U4.1"),
        dict(x=alt["R5via"][0], y=alt["R5via"][1], net="GND", for_="R5.2")]
if alt.get("C6"):
    parts["C6"] = dict(fp="c0603", x=alt["C6"]["x"], y=alt["C6"]["y"], rot=alt["C6"]["rot"])
    vias.append(dict(x=alt["C6"]["via"][0], y=alt["C6"]["via"][1], net="GND", for_="C6.2"))

b = pcbnew.LoadBoard(BOARD_PATH)
# ---- load new footprints BEFORE any Remove (FootprintLoad breaks after it) ----
loaded = {}
for ref, spec in parts.items():
    lib, name, _ = s2.FPDEF[spec["fp"]]
    fp = pcbnew.FootprintLoad(lib, name)
    assert hasattr(fp, "Pads"), f"load failed {name}"
    loaded[ref] = fp
# ---- collect old GND vias + link tracks FIRST (GetTracks breaks after Remove) ----
oldplan = json.load(open(os.path.join(BASE, "tools", "plan.json")))
kill_vias = [(v["x"], v["y"]) for v in oldplan["vias"] if v["for_"] in ("U4.1", "R5.2")]
kill_links = [((0.75, 23.16), (0.25, 23.16)), ((1.65, 27.29), (1.6499999999999997, 26.635))]
def close(a, c, tol=0.06): return abs(a[0] - c[0]) <= tol and abs(a[1] - c[1]) <= tol
kill_tracks = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition(); pt = (TM(p.x), TM(p.y))
        if any(close(pt, kv) for kv in kill_vias):
            kill_tracks.append(t)
    else:
        a = t.GetStart(); c = t.GetEnd()
        pa = (TM(a.x), TM(a.y)); pc = (TM(c.x), TM(c.y))
        for (e1, e2) in kill_links:
            if (close(pa, e1) and close(pc, e2)) or (close(pa, e2) and close(pc, e1)):
                kill_tracks.append(t)
for fp in list(b.GetFootprints()):
    if fp.GetReference() in ("U4", "R4", "R5", "C6", "C7"):
        b.Remove(fp)
removed = 0
for t in kill_tracks:
    b.Remove(t); removed += 1
print(f"removed {removed} old via/link objects (expect 4)")

# ---- place new parts (same pattern as build.py) ----
netobjs = {}
for nm in ("GND", "3V3", "3V3_USB", "3V3_BAT", "PR1", "VBAT"):
    netobjs[nm] = b.FindNet(nm)
placed = {}
for ref, spec in parts.items():
    fp = loaded[ref]
    b.Add(fp)
    fp.SetReference(ref)
    fp.SetValue(bl.VALUES[ref])
    fp.SetPosition(pcbnew.VECTOR2I(MM(spec["x"]), MM(spec["y"])))
    fp.Flip(fp.GetPosition(), False)
    fp.SetOrientationDegrees(spec["rot"])
    nm = bl.NETMAPS[ref]
    for pad in fp.Pads():
        num = pad.GetNumber()
        if num == "" or num not in nm or nm[num] is None:
            continue
        pad.SetNet(netobjs[nm[num]])
    placed[ref] = fp

# ---- verify pad positions + nets against solver model ----
errs = []
for ref, spec in parts.items():
    key = spec["fp"]
    exp = {}
    for (r, num, layers, ctr) in sp.pad_world_rects(s2.GEOM[key]["pads"], spec["x"], spec["y"], spec["rot"], True):
        exp.setdefault(num, []).append(ctr)
    got = {}
    for pad in placed[ref].Pads():
        if pad.GetNumber() == "":
            continue
        ls = pad.GetLayerSet()
        if not (ls.Contains(pcbnew.F_Cu) or ls.Contains(pcbnew.B_Cu)):
            continue
        p = pad.GetPosition()
        got.setdefault(pad.GetNumber(), []).append((TM(p.x), TM(p.y)))
    for num, ctrs_ in exp.items():
        gs = sorted(got.get(num, [])); es = sorted(ctrs_)
        if len(gs) != len(es):
            errs.append(f"{ref}.{num}: count {len(gs)} vs {len(es)}"); continue
        for (gx, gy), (ex, ey) in zip(gs, es):
            if abs(gx - ex) > 0.02 or abs(gy - ey) > 0.02:
                errs.append(f"{ref}.{num}: got ({gx:.2f},{gy:.2f}) expected ({ex:.2f},{ey:.2f})")
    nm = bl.NETMAPS[ref]
    for pad in placed[ref].Pads():
        num = pad.GetNumber()
        if num in nm and nm[num] and pad.GetNetname() != nm[num]:
            errs.append(f"{ref}.{num}: net {pad.GetNetname()!r} != {nm[num]!r}")
if errs:
    print("VERIFY ERRORS:"); [print("  ", e) for e in errs]; sys.exit(1)
print("pad positions + nets verified OK")

# ---- GND vias + link tracks ----
def pad_ctr(ref, num):
    for pad in placed[ref].Pads():
        if pad.GetNumber() == num:
            p = pad.GetPosition(); return (TM(p.x), TM(p.y))
    raise KeyError(ref + "." + num)
gnd = netobjs["GND"]
for v in vias:
    via = pcbnew.PCB_VIA(b)
    via.SetPosition(pcbnew.VECTOR2I(MM(v["x"]), MM(v["y"])))
    via.SetWidth(MM(0.40)); via.SetDrill(MM(0.20))
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(gnd)
    b.Add(via)
    ref, num = v["for_"].split(".")
    (px, py) = pad_ctr(ref, num)
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(MM(px), MM(py)))
    t.SetEnd(pcbnew.VECTOR2I(MM(v["x"]), MM(v["y"])))
    t.SetWidth(MM(0.30)); t.SetLayer(pcbnew.B_Cu); t.SetNet(gnd)
    b.Add(t)
pcbnew.SaveBoard(BOARD_PATH, b)
print("PATCH SAVED")
