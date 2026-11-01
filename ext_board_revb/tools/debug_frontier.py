#!/usr/bin/env python3
"""Print, per x column (1mm), the southernmost B-layer reach of the N-set
(3V3_USB basin from U2.5) and the northernmost reach of the S-set
(3V3_BAT basin), using the relaxed micro model on the clean built board."""
import pcbnew, os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# reuse solve_v3's model construction by executing it up to the BFS sets
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "solve_v3.py")).read()
cut = src.index("# placer obstacles")
exec(src[:cut])
CELL = mr.CELL
def frontier(s, mode):
    out = {}
    for (L, yy, xx) in s:
        if L != 2: continue
        x = xx * CELL
        col = round(x)
        if mode == "max":
            out[col] = max(out.get(col, -1), yy * CELL)
        else:
            out[col] = min(out.get(col, 999), yy * CELL)
    return out
fN = frontier(setN, "max")
fS = frontier(setS, "min")
print(" x   N-max-y   S-min-y")
for x in range(0, 19):
    print(f"{x:3d}  {fN.get(x, -1):7.2f}  {fS.get(x, 999):7.2f}")
