#!/usr/bin/env python3
"""Audit: every REV.A footprint in the REV.B board must match position,
rotation and pad nets exactly. Sole allowed exception: U2 pad 5 net
3V3 -> 3V3_USB (the mux surgery)."""
import pcbnew, os, sys

TM = pcbnew.ToMM
A = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
B = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board_revb/ext_board_revb.kicad_pcb")
ALLOWED = {("U2", "5"): ("3V3", "3V3_USB")}

def fpmap(path):
    b = pcbnew.LoadBoard(path)
    out = {}
    for fp in b.GetFootprints():
        pads = {}
        for pad in fp.Pads():
            p = pad.GetPosition()
            pads.setdefault(pad.GetNumber(), []).append(
                (round(TM(p.x), 3), round(TM(p.y), 3), pad.GetNetname()))
        pos = fp.GetPosition()
        out[fp.GetReference()] = dict(
            pos=(round(TM(pos.x), 3), round(TM(pos.y), 3)),
            rot=round(fp.GetOrientationDegrees() % 360, 1),
            layer="B" if fp.GetLayer() == pcbnew.B_Cu else "F",
            pads={k: sorted(v) for k, v in pads.items()})
    return out

def main():
    a, b = fpmap(A), fpmap(B)
    diffs = []
    for ref, fa in a.items():
        fb = b.get(ref)
        if fb is None:
            diffs.append(f"{ref}: MISSING in REV.B"); continue
        if fa["pos"] != fb["pos"]: diffs.append(f"{ref}: pos {fa['pos']} -> {fb['pos']}")
        if fa["rot"] != fb["rot"]: diffs.append(f"{ref}: rot {fa['rot']} -> {fb['rot']}")
        if fa["layer"] != fb["layer"]: diffs.append(f"{ref}: layer {fa['layer']} -> {fb['layer']}")
        for num, pa in fa["pads"].items():
            pb = fb["pads"].get(num)
            if pb is None:
                diffs.append(f"{ref}.{num}: pad missing"); continue
            if [x[:2] for x in pa] != [x[:2] for x in pb]:
                diffs.append(f"{ref}.{num}: pad pos {pa} -> {pb}"); continue
            for (_, _, na), (_, _, nb) in zip(pa, pb):
                if na != nb:
                    if ALLOWED.get((ref, num)) == (na, nb):
                        print(f"ALLOWED DIFF {ref}.{num}: net {na} -> {nb}")
                    else:
                        diffs.append(f"{ref}.{num}: net {na!r} -> {nb!r}")
    added = sorted(set(b) - set(a))
    print(f"REV.A footprints: {len(a)}, REV.B footprints: {len(b)}, added: {added}")
    if diffs:
        print("AUDIT FAILED:"); [print("  ", d) for d in diffs]; sys.exit(1)
    print("AUDIT PASSED: all REV.A footprints identical (pos/rot/layer/pad pos/pad nets) except the allowed U2.5 net change")

if __name__ == "__main__":
    main()
