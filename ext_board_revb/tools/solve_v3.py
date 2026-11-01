#!/usr/bin/env python3
"""REV.B plan v3: basin-guided mux placement.

Compute BFS reachable sets (micro-router model) from the three anchor
terminals on the built board WITHOUT the old mux cluster:
  N-set: from U2.5 (3V3_USB source)     -> mux VIN1/MODE pads must land here
  S-set: from C5.1 (3V3_BAT source)     -> mux VIN2 pad must land here
  W-set: from J5.1 (3V3 web stub)       -> mux VOUT pads must land here
A mux candidate (pad-clearance valid) is accepted only if every external
pad's center cell lies in the required set. PR1 pad may use N or S
(the divider is placed afterwards near it). GND pad needs a via_spot.
"""
import pcbnew, os, sys, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_place as sp
import solve2 as s2
import micro_route as mr

rt = mr.rt
d = s2.d
check, commit, ctrs = s2.check, s2.commit, s2.ctrs

b = pcbnew.LoadBoard(mr.PATH)
r = rt.R(b)
r.ingest()
# sample copper excluding the old mux cluster pads/tracks/vias
KILL_REFS = ("U4", "R4", "R5")
KILL_XY = [(7.34, 30.3), (7.84, 36.175)]
def close(a, c, tol=0.06): return abs(a[0] - c[0]) <= tol and abs(a[1] - c[1]) <= tol
import numpy as np
copper = [np.zeros((mr.H, mr.W), dtype=np.int32) for _ in range(mr.NL)]
TM, MM, CELL = mr.TM, mr.MM, mr.CELL
for fp in b.GetFootprints():
    if fp.GetReference() in KILL_REFS:
        continue
    for pad in fp.Pads():
        name = pad.GetNetname()
        nid = r.nid(name) if name else rt.OBST
        ls = pad.GetLayerSet()
        if pad.GetDrillSize().x > 0:
            layers = (0, 1, 2)
        else:
            layers = tuple(L for L in (0, 2) if ls.Contains((pcbnew.F_Cu, pcbnew.B_Cu)[L // 2]))
        if not layers: continue
        bb = pad.GetBoundingBox()
        x0, x1 = TM(bb.GetLeft()), TM(bb.GetRight()); y0, y1 = TM(bb.GetTop()), TM(bb.GetBottom())
        ix0 = max(0, int(math.floor(x0 / CELL)) - 1); ix1 = min(mr.W - 1, int(math.ceil(x1 / CELL)) + 1)
        iy0 = max(0, int(math.floor(y0 / CELL)) - 1); iy1 = min(mr.H - 1, int(math.ceil(y1 / CELL)) + 1)
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                if pad.HitTest(pcbnew.VECTOR2I(MM(ix * CELL), MM(iy * CELL)), 0):
                    for L in layers: copper[L][iy, ix] = nid
for t in b.GetTracks():
    name = t.GetNetname()
    if not name: continue
    nid = r.nid(name)
    if t.GetClass() == "PCB_VIA":
        pos = t.GetPosition(); vx, vy = TM(pos.x), TM(pos.y)
        if any(close((vx, vy), k) for k in KILL_XY): continue
        rad = TM(t.GetWidth()) / 2.0 + 0.01
        ix0 = max(0, int((vx - rad) / CELL) - 1); ix1 = min(mr.W - 1, int((vx + rad) / CELL) + 1)
        iy0 = max(0, int((vy - rad) / CELL) - 1); iy1 = min(mr.H - 1, int((vy + rad) / CELL) + 1)
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                if math.hypot(ix * CELL - vx, iy * CELL - vy) <= rad:
                    for L in range(mr.NL): copper[L][iy, ix] = nid
    else:
        L = mr.LAYMAP.get(t.GetLayer())
        if L is None: continue
        a = t.GetStart(); c = t.GetEnd()
        ax, ay, cx, cy = TM(a.x), TM(a.y), TM(c.x), TM(c.y)
        if any(close((ax, ay), k) or close((cx, cy), k) for k in KILL_XY) and name == "GND":
            continue  # the mux/R5 GND link tracks
        hw = TM(t.GetWidth()) / 2.0 + 0.01
        ix0 = max(0, int((min(ax, cx) - hw) / CELL) - 1); ix1 = min(mr.W - 1, int((max(ax, cx) + hw) / CELL) + 1)
        iy0 = max(0, int((min(ay, cy) - hw) / CELL) - 1); iy1 = min(mr.H - 1, int((max(ay, cy) + hw) / CELL) + 1)
        dx, dy = cx - ax, cy - ay; seg2 = dx * dx + dy * dy
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                px, py = ix * CELL, iy * CELL
                if seg2 == 0: dd = math.hypot(px - ax, py - ay)
                else:
                    tt = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
                    dd = math.hypot(px - (ax + tt * dx), py - (ay + tt * dy))
                if dd <= hw: copper[L][iy, ix] = nid
r.copper = copper
r.pads_copper = [c.copy() for c in copper]
r.rebuild_blockers()
print("model ready", flush=True)

def bfs_all(name, exclude_ctr=None):
    # union of endpoints of every pad of the net (the web may be several
    # cell-graph fragments; the true basin is the union of all of them)
    src = {}
    for rec in r.pad_groups[name]:
        if exclude_ctr and d((rec["cx"], rec["cy"]), exclude_ctr) < 1.2:
            continue  # skip the old mux's own pads
        e = r.endpoint(name, rec)
        for L, cells in e.items():
            src.setdefault(L, set()).update(cells)
    return bfs_src(name, src)

def bfs(name, rec):
    return bfs_src(name, r.endpoint(name, rec))

def bfs_src(name, src):
    nid = r.net_ids[name]
    seen = set(); stack = []
    for L, cells in src.items():
        for (y, x) in cells:
            k = (L, y, x)
            if k not in seen: seen.add(k); stack.append(k)
    th = r.th_cells.get(name, set())
    tf = r.track_free; vf = r.via_free
    while stack:
        (L, y, x) = stack.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                nx_, ny_ = x + dx, y + dy
                if not (0 <= nx_ < rt.W and 0 <= ny_ < rt.H): continue
                if not tf(L, ny_, nx_, nid): continue
                if dx != 0 and dy != 0 and not (tf(L, y, nx_, nid) and tf(L, ny_, x, nid)): continue
                k = (L, ny_, nx_)
                if k not in seen: seen.add(k); stack.append(k)
        for oL in range(3):
            if oL == L: continue
            if (y, x) in th or vf(y, x, nid):
                k = (oL, y, x)
                if k not in seen: seen.add(k); stack.append(k)
    return seen

def find_pad(ref, num, net):
    for rec in r.pad_groups[net]:
        pass
    # pad_groups are per net name; find by scanning footprints on the board
    for fp in b.GetFootprints():
        if fp.GetReference() == ref:
            for p in fp.Pads():
                if p.GetNumber() == num:
                    return dict(cx=TM(p.GetPosition().x), cy=TM(p.GetPosition().y),
                                x0=TM(p.GetBoundingBox().GetLeft()), x1=TM(p.GetBoundingBox().GetRight()),
                                y0=TM(p.GetBoundingBox().GetTop()), y1=TM(p.GetBoundingBox().GetBottom()),
                                layers={2}, th=False, name=net)
    raise KeyError(ref + num)

setN = bfs("3V3_USB", find_pad("U2", "5", "3V3_USB"))
print(f"N-set: {len(setN)} cells", flush=True)
setS = bfs_all("3V3_BAT")
print(f"S-set: {len(setS)} cells", flush=True)
setW = bfs_all("3V3", exclude_ctr=(5.6, 30.5))
print(f"W-set: {len(setW)} cells", flush=True)

def cellof(x, y): return (int(round(y / CELL)), int(round(x / CELL)))
MUXPAD = {}
for (rr, num, layers, ctr) in sp.pad_world_rects(s2.GEOM["mux"]["pads"], 0, 0, 0, True):
    MUXPAD[num] = (rr[2] - rr[0], rr[3] - rr[1])  # (w, h) at rot 0
def inset(pt, s, rot, num):
    # member-cell test: any B-layer cell of the pad's shrunk rect in set s
    (w0, h0) = MUXPAD[num]
    (w, h) = (w0, h0) if rot in (0, 180) else (h0, w0)
    x0 = int(math.ceil((pt[0] - w / 2 + 0.06) / CELL)); x1 = int(math.floor((pt[0] + w / 2 - 0.06) / CELL))
    y0 = int(math.ceil((pt[1] - h / 2 + 0.06) / CELL)); y1 = int(math.floor((pt[1] + h / 2 - 0.06) / CELL))
    return any((2, yy, xx) in s for yy in range(y0, y1 + 1) for xx in range(x0, x1 + 1))

# placer obstacles from the same board (includes old mux pads; they sit at
# (5.6,30.5)/(3.64,30.35)/(7.84,36.05) - candidates landing there are bogus
# only if they overlap those exact spots; the basin test uses live pads)
obs, padrects_B = sp.load_obstacles(b)
pl = sp.Placer(obs, padrects_B)
# remove old mux cluster obstacles from the placer by rebuilding without them:
# (their pads are outside most of the scan area; skip - noted in scoring)

U2PAD5 = (6.64, 20.50); C51 = (9.35, 35.08)
cands = []
near = []
for rot in (0, 90, 180, 270):
    cy = 18.6
    while cy <= 36.0:
        cx = 0.9
        while cx <= 17.1:
            ok, _, _ = check(pl, "mux", round(cx, 2), round(cy, 2), rot, s2.MUXNET, "U4")
            if ok:
                c = ctrs("mux", round(cx, 2), round(cy, 2), rot)
                tests = {"3N": inset(c["3"][0], setN, rot, "3"), "5N": inset(c["5"][0], setN, rot, "5"),
                         "6S": inset(c["6"][0], setS, rot, "6"),
                         "2W": inset(c["2"][0], setW, rot, "2"), "7W": inset(c["7"][0], setW, rot, "7"),
                         "4NS": inset(c["4"][0], setN, rot, "4") or inset(c["4"][0], setS, rot, "4")}
                npass = sum(tests.values())
                if npass >= 4:
                    near.append((npass, round(cx, 2), round(cy, 2), rot, {k: v for k, v in tests.items() if not v},
                                 {k: c[k][0] for k in ("2", "3", "5", "6")}))
                if npass == 6:
                    s = (0.8 * d(c["3"][0], U2PAD5) + 1.0 * d(c["6"][0], C51)
                         + 0.5 * d(c["2"][0], (7.09, 24.90)))
                    cands.append((s, round(cx, 2), round(cy, 2), rot))
            cx += 0.1
        cy += 0.1
cands.sort()
near.sort(reverse=True)
print("near misses (passes, x, y, rot, failing, pads 2/3/5/6):", flush=True)
for n in near[:10]: print("  ", n, flush=True)
print(f"basin-valid mux candidates: {len(cands)}", flush=True)
for c in cands[:8]:
    print(f"  score {c[0]:.2f} at ({c[1]},{c[2]}) r{c[3]}", flush=True)
json.dump(cands[:40], open(os.path.join(sp.BASE, "tools", "mux_v3_cands.json"), "w"))
print("CANDS SAVED", flush=True)
