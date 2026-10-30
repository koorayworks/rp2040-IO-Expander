#!/usr/bin/env python3
"""Scan B.Cu for 0603 placements (pads at +-0.825 in Y, 0.8x0.95 pads) whose
pads touch no foreign copper and whose courtyard hits no foreign footprint."""
import pcbnew, os, sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["scan"]
spec.loader.exec_module(rt)

PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
r = rt.R(b)
r.ingest()

# foreign B-side footprint bboxes (exclude R1/R2 themselves)
fps = []
for fp in b.GetFootprints():
    if fp.GetReference() in ("R1", "R2"):
        continue
    if not fp.IsFlipped():
        continue
    bb = fp.GetBoundingBox()
    fps.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()), fp.GetReference()))

def cells_free(cx, cy):
    # pad rect 0.95 x 0.8 centered (cx, cy) on B (rotated 90deg: pads side by side in X)
    x0, x1 = int((cx - 0.475) / 0.05), int((cx + 0.475) / 0.05)
    y0, y1 = int((cy - 0.4) / 0.05), int((cy + 0.4) / 0.05)
    for yy in range(y0, y1 + 1):
        for xx in range(x0, x1 + 1):
            if r.copper[2][yy, xx] != 0:
                return False
            if r.edge_block[yy, xx]:
                return False
    return True

def courtyard_free(cx, cy):
    x0, y0, x1, y1 = cx - 1.05, cy - 1.0, cx + 1.05, cy + 1.0
    for (a, t, c, d, ref) in fps:
        if not (x1 < a or x0 > c or y1 < t or y0 > d):
            return False
    return True

for label, xr in (("CENTER", (5.2, 12.8)),):
    print(label)
    found = []
    xi = xr[0]
    while xi <= xr[1]:
        yi = 5.0
        while yi <= 24.0:
            if cells_free(xi - 0.825, yi) and cells_free(xi + 0.825, yi) and courtyard_free(xi, yi):
                found.append((round(xi, 1), round(yi, 1)))
            yi += 0.4
        xi += 0.4
    print("  candidates:", found[:40])
