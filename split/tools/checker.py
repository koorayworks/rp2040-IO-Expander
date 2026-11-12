#!/usr/bin/env python3
"""Exact-clearance checker for hand-finishing (v2, recreated 2026-11-12
after the /tmp copy was lost to a VM rollback -- this one lives in the
repo). Usage: import from a patch script.

check_seg(board, net, layer, x1, y1, x2, y2, w=0.15)
check_via(board, net, x, y)
  -> (ok, min_clearance, worst_description)
Rules: same-layer tracks/vias/pads for segments; vias are checked on
ALL layers (through vias span the stack) incl. inner-layer tracks;
segments on F/B ignore inner tracks; PTH pads count on every layer.
Same-net items are ignored. Required clearance 0.10 (pass >= 0.099).
"""
import math, pcbnew

mm = 1e6
REQ = 0.099

def _netname(item):
    n = item.GetNet()
    return n.GetNetname() if n else ''

def _seg_pt_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

def _seg_seg_dist(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
    def orient(px, py, qx, qy, rx, ry):
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)
    d1 = orient(x3, y3, x4, y4, x1, y1); d2 = orient(x3, y3, x4, y4, x2, y2)
    d3 = orient(x1, y1, x2, y2, x3, y3); d4 = orient(x1, y1, x2, y2, x4, y4)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(_seg_pt_dist(x1, y1, x3, y3, x4, y4),
               _seg_pt_dist(x2, y2, x3, y3, x4, y4),
               _seg_pt_dist(x3, y3, x1, y1, x2, y2),
               _seg_pt_dist(x4, y4, x1, y1, x2, y2))

def _rect_dist(px, py, rx0, ry0, rx1, ry1):
    dx = max(rx0 - px, 0.0, px - rx1)
    dy = max(ry0 - py, 0.0, py - ry1)
    return math.hypot(dx, dy)

def _seg_rect_dist(seg, r):
    (x1, y1, x2, y2) = seg
    rx0, ry0, rx1, ry1 = r
    if rx0 <= x1 <= rx1 and ry0 <= y1 <= ry1: return 0.0
    if rx0 <= x2 <= rx1 and ry0 <= y2 <= ry1: return 0.0
    edges = [(rx0, ry0, rx1, ry0), (rx1, ry0, rx1, ry1),
             (rx1, ry1, rx0, ry1), (rx0, ry1, rx0, ry0)]
    return min(_seg_seg_dist(seg, e) for e in edges)

def _items(board):
    tracks, vias, pads = [], [], []
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            vias.append((_netname(t), p.x / mm, p.y / mm, t.GetWidth() / mm / 2))
        else:
            s, e = t.GetStart(), t.GetEnd()
            tracks.append((_netname(t), t.GetLayer(),
                           s.x / mm, s.y / mm, e.x / mm, e.y / mm, t.GetWidth() / mm))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pads.append((_netname(pad), pad,
                         bb.GetX() / mm, bb.GetY() / mm,
                         (bb.GetX() + bb.GetWidth()) / mm, (bb.GetY() + bb.GetHeight()) / mm))
    return tracks, vias, pads

def _pad_layers(pad):
    ls = pad.GetLayerSet()
    out = set()
    for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        if ls.Contains(l):
            out.add(l)
    return out

def check_seg(board, net, layer, x1, y1, x2, y2, w=0.15):
    tracks, vias, pads = _items(board)
    seg = (x1, y1, x2, y2)
    worst, desc = 9e9, ''
    for (n, l, a, b, c, d, tw) in tracks:
        if n == net or l != layer:
            continue
        dist = _seg_seg_dist(seg, (a, b, c, d)) - w / 2 - tw / 2
        if dist < worst:
            worst, desc = dist, f'track[{n}]@({a:.2f},{b:.2f})-({c:.2f},{d:.2f}) L{l}'
    for (n, vx, vy, r) in vias:
        if n == net:
            continue
        dist = _seg_pt_dist(vx, vy, x1, y1, x2, y2) - w / 2 - r
        if dist < worst:
            worst, desc = dist, f'via[{n}]@({vx:.2f},{vy:.2f})'
    for (n, pad, rx0, ry0, rx1, ry1) in pads:
        if n == net or layer not in _pad_layers(pad):
            continue
        dist = _seg_rect_dist(seg, (rx0, ry0, rx1, ry1)) - w / 2
        if dist < worst:
            worst, desc = dist, f'pad[{n}] {pad.GetParentFootprint().GetReference()}.{pad.GetNumber()}'
    return worst >= REQ, worst, desc

def check_via(board, net, x, y):
    tracks, vias, pads = _items(board)
    r = 0.45 / 2
    worst, desc = 9e9, ''
    for (n, l, a, b, c, d, tw) in tracks:
        if n == net:
            continue
        dist = _seg_pt_dist(x, y, a, b, c, d) - r - tw / 2
        if dist < worst:
            worst, desc = dist, f'track[{n}]@({a:.2f},{b:.2f})-({c:.2f},{d:.2f}) L{l}'
    for (n, vx, vy, vr) in vias:
        if n == net:
            continue
        dist = math.hypot(x - vx, y - vy) - r - vr
        if dist < worst:
            worst, desc = dist, f'via[{n}]@({vx:.2f},{vy:.2f})'
    for (n, pad, rx0, ry0, rx1, ry1) in pads:
        if n == net:
            continue
        # through via sees PTH pads on all layers and SMD pads too
        # (annulus exists on F and B at minimum)
        dist = _rect_dist(x, y, rx0, ry0, rx1, ry1) - r
        if dist < worst:
            worst, desc = dist, f'pad[{n}] {pad.GetParentFootprint().GetReference()}.{pad.GetNumber()}'
    return worst >= REQ, worst, desc
