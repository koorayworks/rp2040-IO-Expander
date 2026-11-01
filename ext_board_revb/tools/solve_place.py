#!/usr/bin/env python3
"""REV.B placement solver: continuous-geometry clearance checks against the
post-surgery REV.A board. Finds positions for U4 (mux), divider, boost
cluster (U3/L1/C4/C5), J7 (battery connector), SW1 (slide switch)."""
import pcbnew, os, sys, math, json, re
import importlib.util

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board_revb")
SRC = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board")
TM = pcbnew.ToMM
CLR = 0.12          # pad clearance design margin (DRC min is 0.10)
LAY = {"F": pcbnew.F_Cu, "In2": pcbnew.In2_Cu, "B": pcbnew.B_Cu}

# ---------------- geometry helpers ----------------
def rect_dist(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    if dx == 0 and dy == 0:
        # overlap or touching: negative = penetration depth (approx)
        ox = min(a[2], b[2]) - max(a[0], b[0])
        oy = min(a[3], b[3]) - max(a[1], b[1])
        return -min(ox, oy)
    return math.hypot(dx, dy)

def pt_rect_dist(px, py, r):
    dx = max(r[0] - px, px - r[2], 0.0)
    dy = max(r[1] - py, py - r[3], 0.0)
    if dx == 0 and dy == 0:
        return -min(px - r[0], r[2] - px, py - r[1], r[3] - py)
    return math.hypot(dx, dy)

def seg_pt_dist(ax, ay, bx, by, px, py):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))

def seg_rect_dist(ax, ay, bx, by, r):
    # 0 if segment intersects rect
    if r[0] <= ax <= r[2] and r[1] <= ay <= r[3]: return 0.0
    if r[0] <= bx <= r[2] and r[1] <= by <= r[3]: return 0.0
    # segment vs rect edges (crossing test via orientation)
    def cross(ox, oy, ax_, ay_, bx_, by_):
        return (ax_ - ox) * (by_ - oy) - (ay_ - oy) * (bx_ - ox)
    def seg_int(a, b, c, d):
        d1 = cross(c[0], c[1], d[0], d[1], a[0], a[1]); d2 = cross(c[0], c[1], d[0], d[1], b[0], b[1])
        d3 = cross(a[0], a[1], b[0], b[1], c[0], c[1]); d4 = cross(a[0], a[1], b[0], b[1], d[0], d[1])
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))
    A = (ax, ay); B = (bx, by)
    corners = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    for i in range(4):
        if seg_int(A, B, corners[i], corners[(i + 1) % 4]): return 0.0
    d = min(pt_rect_dist(ax, ay, r), pt_rect_dist(bx, by, r))
    for (cx, cy) in corners:
        d = min(d, seg_pt_dist(ax, ay, bx, by, cx, cy))
    return d

def rect_circle_dist(r, cx, cy, cr):
    return pt_rect_dist(cx, cy, r) - cr

def rect_capsule_dist(r, ax, ay, bx, by, cr):
    return seg_rect_dist(ax, ay, bx, by, r) - cr

# ---------------- board obstacles ----------------
def load_obstacles(board):
    """returns dict layer->list of (kind, data, net); kind rect/circ/caps"""
    obs = {"F": [], "In2": [], "B": []}
    padrects_B = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            ls = pad.GetLayerSet()
            layers = []
            if pad.GetDrillSize().x > 0:
                layers = ["F", "In2", "B"]
            else:
                if ls.Contains(pcbnew.F_Cu): layers.append("F")
                if ls.Contains(pcbnew.In2_Cu): layers.append("In2")
                if ls.Contains(pcbnew.B_Cu): layers.append("B")
            if not layers: continue
            bb = pad.GetBoundingBox()
            r = (TM(bb.GetLeft()), TM(bb.GetTop()), TM(bb.GetRight()), TM(bb.GetBottom()))
            net = pad.GetNetname()
            for L in layers:
                obs[L].append(("rect", r, net))
            if "B" in layers:
                padrects_B.append((r, net, fp.GetReference()))
    for t in board.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition(); cr = TM(t.GetWidth()) / 2
            for L in ("F", "In2", "B"):
                obs[L].append(("circ", (TM(p.x), TM(p.y), cr), net))
        else:
            ln = {pcbnew.F_Cu: "F", pcbnew.In2_Cu: "In2", pcbnew.B_Cu: "B"}.get(t.GetLayer())
            if ln is None: continue
            s, e = t.GetStart(), t.GetEnd()
            obs[ln].append(("caps", (TM(s.x), TM(s.y), TM(e.x), TM(e.y), TM(t.GetWidth()) / 2), net))
    return obs, padrects_B

def dist_to_obs(r, layer, obs_list, net):
    """min distance from rect r to foreign-net obstacles on layer; net None=NC (all foreign)"""
    best = 99.0; who = None
    for (kind, data, onet) in obs_list:
        if net is not None and onet == net and net != "":
            continue
        if kind == "rect":
            d = rect_dist(r, data)
        elif kind == "circ":
            d = rect_circle_dist(r, data[0], data[1], data[2])
        else:
            d = rect_capsule_dist(r, data[0], data[1], data[2], data[3], data[4])
        if d < best:
            best = d; who = (kind, onet)
    return best, who

# ---------------- footprint local geometry (parse .kicad_mod) ----------------
def parse_fp(path):
    t = open(path).read()
    pads = []
    for m in re.finditer(r'\(pad\s+"([^"]*)"\s+(\w+)\s+(\w+)', t):
        i = m.start(); depth = 0; j = i
        while True:
            if t[j] == '(': depth += 1
            elif t[j] == ')':
                depth -= 1
                if depth == 0: break
            j += 1
        blk = t[i:j + 1]
        at = re.search(r'\(at\s+([\d.\-]+)\s+([\d.\-]+)(?:\s+([\d.\-]+))?', blk)
        sz = re.search(r'\(size\s+([\d.]+)\s+([\d.]+)\)', blk)
        lay = re.search(r'\(layers\s+([^)]*)\)', blk).group(1)
        dr = re.search(r'\(drill\s+([\d.]+)', blk)
        pads.append(dict(num=m.group(1), type=m.group(2),
                         x=float(at.group(1)), y=float(at.group(2)),
                         rot=float(at.group(3) or 0),
                         w=float(sz.group(1)), h=float(sz.group(2)),
                         layers=lay, drill=float(dr.group(1)) if dr else 0.0))
    def layer_bbox(layer):
        pts = []
        for m in re.finditer(r'\(fp_line\s+\(start ([\d.\-]+) ([\d.\-]+)\)\s+\(end ([\d.\-]+) ([\d.\-]+)\)\s+\(stroke.*?\)\s+\(layer "' + layer + r'"\)', t, re.S):
            a, b, c, d = map(float, m.groups()); pts += [(a, b), (c, d)]
        for m in re.finditer(r'\(fp_rect\s+\(start ([\d.\-]+) ([\d.\-]+)\)\s+\(end ([\d.\-]+) ([\d.\-]+)\).*?\(layer "' + layer + r'"\)', t, re.S):
            a, b, c, d = map(float, m.groups()); pts += [(a, b), (c, d)]
        if not pts: return None
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
    return pads, layer_bbox("F.Fab"), layer_bbox("F.CrtYd")

def xform(lx, ly, rot, flip):
    if flip: ly = -ly
    th = math.radians(rot); c, s = math.cos(th), math.sin(th)
    return (lx * c + ly * s, -lx * s + ly * c)

def rect_xform(rect, rot, flip):
    pts = [xform(rect[0], rect[1], rot, flip), xform(rect[2], rect[1], rot, flip),
           xform(rect[0], rect[3], rot, flip), xform(rect[2], rect[3], rot, flip)]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))

def pad_world_rects(pads, cx, cy, rot, flip):
    """world rects for copper pads only. Returns list of (rect, num, layers)"""
    out = []
    for p in pads:
        if '"F.Cu"' not in p["layers"] and '"B.Cu"' not in p["layers"] and "*.Cu" not in p["layers"]:
            continue
        # local rect (account pad's own rotation: only 0/90 in our parts)
        w, h = p["w"], p["h"]
        lr = (p["x"] - w / 2, p["y"] - h / 2, p["x"] + w / 2, p["y"] + h / 2)
        wr = rect_xform(lr, rot, flip)
        ls = []
        if p["drill"] > 0: ls = ["F", "In2", "B"]
        else: ls = ["B"] if flip else ["F"]
        out.append(((wr[0] + cx, wr[1] + cy, wr[2] + cx, wr[3] + cy), p["num"], ls,
                    (cx + xform(p["x"], p["y"], rot, flip)[0], cy + xform(p["x"], p["y"], rot, flip)[1])))
    return out

# ---------------- surgery (shared with builder) ----------------
def do_surgery(board):
    nets = {}
    for name in ("3V3_USB", "VBAT", "BAT_IN", "3V3_BAT", "BOOST_SW", "PR1"):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
    kill = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA": continue
        if t.GetLayer() != pcbnew.B_Cu: continue
        if t.GetNetname() != "3V3": continue
        s = (round(TM(t.GetStart().x), 2), round(TM(t.GetStart().y), 2))
        e = (round(TM(t.GetEnd().x), 2), round(TM(t.GetEnd().y), 2))
        pair = {s, e}
        if pair == {(6.64, 20.50), (6.64, 19.81)} or pair == {(6.64, 20.50), (7.44, 21.31)}:
            kill.append(t)
    for t in kill: board.Remove(t)
    assert len(kill) == 2, f"surgery: expected 2 segments, got {len(kill)}"
    for fp in board.GetFootprints():
        if fp.GetReference() == "U2":
            for pad in fp.Pads():
                if pad.GetNumber() == "5":
                    pad.SetNet(nets["3V3_USB"])
    for d in board.GetDrawings():
        if d.GetClass() == "PCB_TEXT" and d.GetText() == "ZERO-WIRELESS EXT REV.A":
            d.SetText("ZERO-WIRELESS EXT REV.B")
    return nets

# ---------------- candidate checking ----------------
REVA_BODIES = [  # (rect, name) B-side REV.A component bodies to avoid
    ((4.05, 18.65), (6.95, 20.45), "U2 body"),
    ((12.55, 19.45), (14.25, 20.35), "C1 body"),
    ((11.80, 17.05), (12.60, 18.65), "C2 body"),
    ((3.60, 10.90), (14.40, 16.70), "J4 housing"),
    ((3.60, 5.20), (14.40, 11.00), "J3 housing"),
    ((2.40, 11.80), (4.00, 12.60), "R1 body"),
    ((13.80, 11.80), (15.40, 12.60), "R2 body"),
]
CAN_F = (3.80, 26.30, 14.20, 41.80)   # module can on F (for THT pin check; n/a for SMD)
KEEP = (4.35, 38.00, 13.65, 43.50)

def obs_bbox(kind, data):
    if kind == "rect": return data
    if kind == "circ": return (data[0] - data[2], data[1] - data[2], data[0] + data[2], data[1] + data[2])
    return (min(data[0], data[2]) - data[4], min(data[1], data[3]) - data[4],
            max(data[0], data[2]) + data[4], max(data[1], data[3]) + data[4])

class Placer:
    def __init__(self, obs, padrects_B):
        self.obs = obs
        self.padrects_B = padrects_B
        self.placed = []   # (rect, net, layer, mindim) new pads
        self.bodies = []   # (rect, name) new bodies
        self.clr = CLR
        # spatial hash, 2mm buckets
        from collections import defaultdict
        self.hash = {}
        for L, lst in obs.items():
            h = defaultdict(list)
            for ob in lst:
                bb = obs_bbox(ob[0], ob[1])
                for gx in range(int(bb[0] // 2), int(bb[2] // 2) + 1):
                    for gy in range(int(bb[1] // 2), int(bb[3] // 2) + 1):
                        h[(gx, gy)].append(ob)
            self.hash[L] = h

    def obs_near(self, L, r, m=0.6):
        seen = set(); out = []
        for gx in range(int((r[0] - m) // 2), int((r[2] + m) // 2) + 1):
            for gy in range(int((r[1] - m) // 2), int((r[3] + m) // 2) + 1):
                for ob in self.hash[L].get((gx, gy), []):
                    if id(ob) not in seen:
                        seen.add(id(ob)); out.append(ob)
        return out

    def check_part(self, pads, cx, cy, rot, flip, netmap, body_local, name, full=False):
        """netmap: padnum -> net (None for NC). Returns (ok, worst_margin, info).
        full=True: no early exit; worst is the true minimum margin over all checks."""
        wrs = pad_world_rects(pads, cx, cy, rot, flip)
        worst = 99.0; info = ""
        fail = False
        for (r, num, layers, ctr) in wrs:
            net = netmap.get(num, None)
            for L in layers:
                near = self.obs_near(L, r)
                if net is None:  # NC pad: everything is foreign
                    d, who = dist_to_obs(r, L, near, "__NC__")
                else:
                    d, who = dist_to_obs(r, L, near, net)
                if d < worst: worst, info = d, f"{name}.{num} vs {who} on {L}"
                if d < self.clr:
                    if not full: return (False, d, info)
                    fail = True
                # vs placed new pads
                for (pr, pnet, pL, pmd) in self.placed:
                    if pL != L: continue
                    if net is not None and pnet == net: continue
                    d2 = rect_dist(r, pr)
                    if d2 < worst: worst, info = d2, f"{name}.{num} vs placed {pnet}"
                    if d2 < self.clr:
                        if not full: return (False, d2, info)
                        fail = True
            # antenna keepout: no new copper within 0.15 of the rule area
            dk = rect_dist(r, KEEP)
            if dk < 0.15:
                if dk < worst: worst, info = dk, f"{name}.{num} near antenna keepout"
                if not full: return (False, dk, info)
                fail = True
        # body checks
        if body_local:
            br = rect_xform(body_local, rot, flip)
            br = (br[0] + cx, br[1] + cy, br[2] + cx, br[3] + cy)
            body_fail = None
            if br[0] < -0.01 or br[1] < -0.01 or br[2] > 18.01 or br[3] > 43.51:
                body_fail = f"{name} body off board {br}"
            if body_fail is None:
                for (pr, pnet, ref) in self.padrects_B:
                    d = rect_dist(br, pr)
                    if d < 0.05: body_fail = f"{name} body over REV.A pad {ref}"; break
            if body_fail is None:
                for (bb, bn) in [( (b[0][0], b[0][1], b[1][0], b[1][1]), b[2]) for b in REVA_BODIES]:
                    d = rect_dist(br, bb)
                    if d < 0.20: body_fail = f"{name} body vs {bn}"; break
            if body_fail is None:
                for (pb, pn) in self.bodies:
                    d = rect_dist(br, pb)
                    if d < 0.30: body_fail = f"{name} body vs placed {pn}"; break
            if body_fail is None and br[2] > KEEP[0] and br[0] < KEEP[2] and br[3] > KEEP[1]:
                body_fail = f"{name} body in antenna keepout"
            if body_fail is not None:
                if not full: return (False, -1, body_fail)
                fail = True; info = "BODY: " + body_fail + " | " + info
        return (not fail, worst, info)

    def commit_part(self, pads, cx, cy, rot, flip, netmap, body_local, name):
        for (r, num, layers, ctr) in pad_world_rects(pads, cx, cy, rot, flip):
            net = netmap.get(num, None)
            md = min(r[2] - r[0], r[3] - r[1])
            for L in layers:
                self.placed.append((r, net if net else "__NC__", L, md))
        if body_local:
            br = rect_xform(body_local, rot, flip)
            self.bodies.append(((br[0] + cx, br[1] + cy, br[2] + cx, br[3] + cy), name))

    def via_spot(self, cx, cy, maxr, net="GND", avoid=()):
        """find a via center within maxr of (cx,cy): via r=0.20 clears foreign copper >=0.10
        on all layers. In-pad allowed only on same-net placed pads with mindim>=0.55
        (EP / mounting tabs) when the via center sits inside the pad shrunk by 0.21.
        avoid: rects the via must keep >=0.05 from regardless of net."""
        best = None
        steps = int(maxr / 0.05)
        for dy in range(-steps, steps + 1):
            for dx in range(-steps, steps + 1):
                vx, vy = cx + dx * 0.05, cy + dy * 0.05
                if math.hypot(dx * 0.05, dy * 0.05) > maxr: continue
                ok = True
                vr = (vx - 0.2, vy - 0.2, vx + 0.2, vy + 0.2)
                for L in ("F", "In2", "B"):
                    d, _ = dist_to_obs(vr, L, self.obs_near(L, vr), net)
                    if d < 0.10: ok = False; break
                if ok:
                    for ar in avoid:
                        if rect_dist(vr, ar) < 0.05: ok = False; break
                if ok:
                    for (pr, pnet, pL, pmd) in self.placed:
                        if rect_dist(vr, pr) >= 0.10: continue
                        inpad = (pnet == net and pmd >= 0.55
                                 and pr[0] + 0.21 <= vx <= pr[2] - 0.21
                                 and pr[1] + 0.21 <= vy <= pr[3] - 0.21)
                        if not inpad: ok = False; break
                if ok:
                    dd = math.hypot(vx - cx, vy - cy)
                    if best is None or dd < best[2]: best = (vx, vy, dd)
        return best

def main():
    b = pcbnew.LoadBoard(os.path.join(BASE, "ext_board_revb.kicad_pcb"))
    do_surgery(b)
    obs, padrects_B = load_obstacles(b)
    pl = Placer(obs, padrects_B)
    L = "/usr/share/kicad/footprints"
    fps = {}
    fps["mux"] = parse_fp(os.path.join(BASE, "revb.pretty", "TPS2116DRLR.kicad_mod"))
    fps["u3"] = parse_fp(f"{L}/Package_DFN_QFN.pretty/DFN-6-1EP_2x2mm_P0.65mm_EP1x1.6mm.kicad_mod")
    fps["l1"] = parse_fp(f"{L}/Inductor_SMD.pretty/L_1008_2520Metric.kicad_mod")
    fps["c0603"] = parse_fp(f"{L}/Capacitor_SMD.pretty/C_0603_1608Metric.kicad_mod")
    fps["r0603"] = parse_fp(f"{L}/Resistor_SMD.pretty/R_0603_1608Metric.kicad_mod")
    fps["j7"] = parse_fp(f"{L}/Connector_JST.pretty/JST_PH_B2B-PH-SM4-TB_1x02-1MP_P2.00mm_Vertical.kicad_mod")
    fps["sw1"] = parse_fp(f"{L}/Button_Switch_SMD.pretty/Nidec_Copal_CAS-120A.kicad_mod")
    for k, (pads, fab, crt) in fps.items():
        print(k, "pads:", [(p["num"], p["x"], p["y"], p["w"], p["h"]) for p in pads if '"F.Cu"' in p["layers"] or "*.Cu" in p["layers"]], "fab:", fab, "crtyd:", crt)
    json.dump({k: dict(n_pads=len(v[0])) for k, v in fps.items()}, open("/tmp/fp_check.json", "w"))
    # save parsed geometry for later steps
    out = {}
    for k, (pads, fab, crt) in fps.items():
        out[k] = dict(pads=pads, fab=fab, crt=crt)
    json.dump(out, open(os.path.join(BASE, "tools", "fp_geom.json"), "w"), indent=1)
    print("geometry saved")

if __name__ == "__main__":
    main()
