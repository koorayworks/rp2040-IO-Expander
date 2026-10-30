#!/usr/bin/env python3
"""Heal v7: for a (JLEG pad, short fragment track) DRC pair, extend the
fragment itself: draw a track from the fragment's endpoint nearest the
pad straight to the pad centre (same layer). No model check (the line
hugs the existing track); verified afterwards by DRC.
Usage: heal7.py NET FRAG_LEN LAYER_NAME — or read pairs from DRC json:
       heal7.py /path/to/drc.json"""
import pcbnew, os, sys, math, json, re
import importlib.util

DRC_ARG = sys.argv[1] if len(sys.argv) > 1 else None
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["heal7"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LAYMAP = {"F.Cu": 0, "In2.Cu": 1, "B.Cu": 2}
JLEG = {
    "GPIO0": (16.67, 1.59), "GPIO1": (16.67, 4.13), "GPIO2": (16.67, 6.67),
    "GPIO3": (16.67, 9.21), "GPIO4": (16.67, 11.75), "GPIO5": (16.67, 14.29),
    "GPIO6": (16.67, 16.83), "GPIO7": (16.67, 19.37), "GPIO8": (16.67, 21.91),
    "GPIO9": (14.08, 21.96), "GPIO10": (11.54, 21.96), "GPIO11": (9.0, 21.96),
    "GPIO12": (6.46, 21.96), "GPIO13": (3.92, 21.96), "GPIO14": (1.33, 21.91),
    "GPIO15": (1.33, 19.37), "GPIO26": (1.33, 16.83), "GPIO27": (1.33, 14.29),
    "GPIO28": (1.33, 11.75), "GPIO29": (1.33, 9.21), "3V3": (1.33, 6.67),
}

def seg_len(t):
    s = t.GetStart(); e = t.GetEnd()
    return math.hypot(pcbnew.ToMM(e.x - s.x), pcbnew.ToMM(e.y - s.y))

def main():
    d = json.load(open(DRC_ARG))
    targets = {}
    for it in d["unconnected_items"]:
        items = it["items"]
        if len(items) != 2:
            continue
        descs = [i["description"] for i in items]
        pad_item = next((x for x in descs if "of JLEG" in x), None)
        trk_item = next((x for x in descs if x.startswith("Track")), None)
        if not pad_item or not trk_item:
            continue
        m = re.search(r"\[([^\]]+)\]", trk_item)
        ln = re.search(r"length ([\d.]+) mm", trk_item)
        lm = re.search(r"on (\S+),", trk_item)
        if m and ln and lm and m.group(1) in JLEG:
            targets[m.group(1)] = (float(ln.group(1)), LAYMAP[lm.group(1)])
    print("heal7 targets:", targets)
    b = pcbnew.LoadBoard(PATH)
    all_tracks = list(b.GetTracks())
    for net, (flen, L) in targets.items():
        px, py = JLEG[net]
        frag = None
        for t in all_tracks:
            if t.GetNetname() != net or t.GetClass() == "PCB_VIA":
                continue
            if {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}.get(t.GetLayer()) != L:
                continue
            if abs(seg_len(t) - flen) > 0.03:
                continue
            s = t.GetStart(); e = t.GetEnd()
            mx, my = pcbnew.ToMM((s.x + e.x) // 2), pcbnew.ToMM((s.y + e.y) // 2)
            if math.hypot(mx - px, my - py) < 2.0:
                frag = t
                break
        if frag is None:
            print(net, "fragment not found")
            continue
        s = frag.GetStart(); e = frag.GetEnd()
        a = (pcbnew.ToMM(s.x), pcbnew.ToMM(s.y))
        c = (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y))
        src = a if math.hypot(a[0] - px, a[1] - py) < math.hypot(c[0] - px, c[1] - py) else c
        t2 = pcbnew.PCB_TRACK(b)
        t2.SetStart(pcbnew.VECTOR2I(MM(src[0]), MM(src[1])))
        t2.SetEnd(pcbnew.VECTOR2I(MM(px), MM(py)))
        t2.SetWidth(MM(0.10))
        t2.SetLayer(LAYERS[L])
        t2.SetNet(b.FindNet(net))
        b.Add(t2)
        print(net, "extended fragment", src, "-> pad centre on layer", L)
    pcbnew.SaveBoard(PATH, b)
    print("HEAL7 DONE")

if __name__ == "__main__":
    main()
