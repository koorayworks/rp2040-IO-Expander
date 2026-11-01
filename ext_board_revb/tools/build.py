#!/usr/bin/env python3
"""REV.B builder: surgery + place planned footprints + GND vias, verify pad
positions against the solver model, save. Routing is a separate step."""
import pcbnew, os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2

BASE = sp.BASE
MM = pcbnew.FromMM; TM = pcbnew.ToMM
BOARD_PATH = os.path.join(BASE, "ext_board_revb.kicad_pcb")

VALUES = {"U3": "TPS610994DRVR", "L1": "2.2uH 2520", "C4": "10uF 0603", "C5": "10uF 0603",
          "C6": "100nF 0603", "C7": "100nF 0603", "U4": "TPS2116DRLR", "R4": "180k 0603",
          "R5": "100k 0603", "J7": "BAT THT pads", "SW1": "CAS-120A"}
NETMAPS = {
    "U4": s2.MUXNET,
    "U3": {"1": "GND", "2": "3V3_BAT", "3": "GND", "4": "VBAT", "5": "BOOST_SW", "6": "VBAT", "7": "GND"},
    "L1": {"1": "BOOST_SW", "2": "3V3_BAT"},
    "C4": {"1": "VBAT", "2": "GND"}, "C5": {"1": "3V3_BAT", "2": "GND"},
    "C6": {"1": "3V3_USB", "2": "GND"}, "C7": {"1": "3V3_BAT", "2": "GND"},
    "R4": {"1": "3V3_USB", "2": "PR1"}, "R5": {"1": "PR1", "2": "GND"},
    "SW1": {"1": "BAT_IN", "2": "VBAT", "3": None},
    "J7": {"1": "BAT_IN", "2": "GND"},
}

def add_j7p(board, spec, netobjs):
    """Construct the 2x THT battery pad footprint (donor: JST PH THT pad)."""
    src = pcbnew.FootprintLoad("/usr/share/kicad/footprints/Connector_JST.pretty",
                               "JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical")
    donor = list(src.Pads())[0]
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference("J7")
    fp.SetValue(VALUES["J7"])
    pads = {}
    for num in ("1", "2"):
        pad = pcbnew.PAD(donor)   # copy ctor: layers/attrib inherited
        pad.SetParent(fp)
        pad.SetNumber(num)
        pad.SetSize(pcbnew.VECTOR2I(MM(1.7), MM(1.7)))
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(0.9), MM(0.9)))
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetNet(netobjs[NETMAPS["J7"][num]])
        fp.Add(pad)
        pads[num] = pad
    board.Add(fp)
    fp.SetPosition(pcbnew.VECTOR2I(MM(spec["x"]), MM(spec["y"])))
    fp.SetOrientationDegrees(spec["rot"])
    # set exact world pad centers from the solver model
    for (r, num, layers, ctr) in sp.pad_world_rects(s2.GEOM["j7p"]["pads"], spec["x"], spec["y"], spec["rot"], False):
        pads[num].SetPosition(pcbnew.VECTOR2I(MM(ctr[0]), MM(ctr[1])))
    return fp

def main():
    plan = json.load(open(os.path.join(BASE, "tools", "plan.json")))
    b = pcbnew.LoadBoard(BOARD_PATH)
    netobjs = sp.do_surgery(b)
    for name in ("GND", "3V3"):
        netobjs[name] = b.FindNet(name)
    placed = {}
    for ref, spec in plan["parts"].items():
        key = spec["fp"]
        if key == "j7p":
            fp = add_j7p(b, spec, netobjs)
        else:
            lib, name, _ = s2.FPDEF[key]
            fp = pcbnew.FootprintLoad(lib, name + ".kicad_mod" if False else name)
            assert hasattr(fp, "Pads"), f"load failed {name}"
            b.Add(fp)
            fp.SetReference(ref)
            fp.SetValue(VALUES[ref])
            fp.SetPosition(pcbnew.VECTOR2I(MM(spec["x"]), MM(spec["y"])))
            fp.Flip(fp.GetPosition(), False)
            fp.SetOrientationDegrees(spec["rot"])
            nm = NETMAPS[ref]
            for pad in fp.Pads():
                num = pad.GetNumber()
                if num == "" or num not in nm: continue
                if nm[num] is None: continue
                pad.SetNet(netobjs[nm[num]])
        placed[ref] = fp
    # ---- verify pad world positions against solver model ----
    errs = []
    for ref, spec in plan["parts"].items():
        key = spec["fp"]
        exp = {}
        for (r, num, layers, ctr) in sp.pad_world_rects(s2.GEOM[key]["pads"], spec["x"], spec["y"], spec["rot"], key != "j7p"):
            exp.setdefault(num, []).append(ctr)
        got = {}
        for pad in placed[ref].Pads():
            if pad.GetNumber() == "": continue
            ls = pad.GetLayerSet()
            if not (ls.Contains(pcbnew.F_Cu) or ls.Contains(pcbnew.B_Cu)): continue
            p = pad.GetPosition()
            got.setdefault(pad.GetNumber(), []).append((TM(p.x), TM(p.y)))
        for num, ctrs_ in exp.items():
            gs = sorted(got.get(num, []))
            es = sorted(ctrs_)
            if len(gs) != len(es):
                errs.append(f"{ref}.{num}: count {len(gs)} vs expected {len(es)}"); continue
            for (gx, gy), (ex, ey) in zip(gs, es):
                if abs(gx - ex) > 0.02 or abs(gy - ey) > 0.02:
                    errs.append(f"{ref}.{num}: got ({gx:.2f},{gy:.2f}) expected ({ex:.2f},{ey:.2f})")
        # net check
        nm = NETMAPS[ref]
        for pad in placed[ref].Pads():
            num = pad.GetNumber()
            if num in nm and nm[num]:
                if pad.GetNetname() != nm[num]:
                    errs.append(f"{ref}.{num}: net {pad.GetNetname()!r} != {nm[num]!r}")
    if errs:
        print("VERIFY ERRORS:"); [print("  ", e) for e in errs]; sys.exit(1)
    print("pad positions + nets verified OK")
    # ---- GND vias + short links ----
    def pad_ctr(ref, num):
        for pad in placed[ref].Pads():
            if pad.GetNumber() == num:
                p = pad.GetPosition(); return (TM(p.x), TM(p.y))
        raise KeyError(ref + "." + num)
    gnd = netobjs["GND"]
    for v in plan["vias"]:
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(pcbnew.VECTOR2I(MM(v["x"]), MM(v["y"])))
        via.SetWidth(MM(0.40)); via.SetDrill(MM(0.20))
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(gnd)
        b.Add(via)
        fo = v.get("for_", "")
        if fo and "." in fo and not fo.endswith("EP") and abs(v["x"] - pad_ctr(fo.split(".")[0], fo.split(".")[1])[0]) + abs(v["y"] - pad_ctr(fo.split(".")[0], fo.split(".")[1])[1]) > 0.01:
            ref, num = fo.split(".")
            (px, py) = pad_ctr(ref, num)
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(MM(px), MM(py)))
            t.SetEnd(pcbnew.VECTOR2I(MM(v["x"]), MM(v["y"])))
            t.SetWidth(MM(0.30)); t.SetLayer(pcbnew.B_Cu); t.SetNet(gnd)
            b.Add(t)
    # U3 pin1 (GND) -> EP link track (2 segments, detour S of U3.2 pad)
    (x1, y1) = pad_ctr("U3", "1"); (x7, y7) = pad_ctr("U3", "7")
    for (ax, ay), (bx, by) in [((x1, y1), (9.60, 32.50)), ((9.60, 32.50), (x7, y7))]:
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay))); t.SetEnd(pcbnew.VECTOR2I(MM(bx), MM(by)))
        t.SetWidth(MM(0.30)); t.SetLayer(pcbnew.B_Cu); t.SetNet(gnd)
        b.Add(t)
    # J7 silk labels on B
    j7 = plan["parts"]["J7"]
    rects = {}
    for pad in placed["J7"].Pads():
        p = pad.GetPosition(); rects[pad.GetNumber()] = (TM(p.x), TM(p.y))
    (ax, ay) = rects["1"]; (bx, by) = rects["2"]
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy); px, py = dy / L, -dx / L   # perpendicular
    if px > 0: px, py = -px, -py                        # prefer west side
    for (cx, cy, txt) in ((ax, ay, "BAT+"), (bx, by, "GND")):
        t = pcbnew.PCB_TEXT(b)
        t.SetText(txt)
        t.SetPosition(pcbnew.VECTOR2I(MM(cx + px * 2.1), MM(cy + py * 2.1)))
        t.SetLayer(pcbnew.B_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
        t.SetTextThickness(MM(0.12))
        b.Add(t)
    pcbnew.SaveBoard(BOARD_PATH, b)
    print("BUILD SAVED")

if __name__ == "__main__":
    main()
