#!/usr/bin/env python3
"""TPS61099 conversion, Phase 2 (final, applied 2026-11-17).

Phase 1 (already in the board, see backup/pre_tps61099_20261116.kicad_pcb
for the pre-conversion state) changed U3's value to TPS61099DRVR and
re-pointed pad 3 from GND to the new BOOST_FB net with a B.Cu thread
(6.55,28.95)->(6.82,28.95)->(6.82,28.35)->(7.47,28.30)->run to (7.47,26.60).

This script adds, on BOARD_PATH:
 0. J3.6 pad trim: size 0.30x1.20, center y -> 28.05 (clears the latent
    0.025mm clearance to U3.3 created by Phase 1's thread).
 1. Feedback divider (TPS61099 VREF = 1.00V):
    R14 = 249k 0402 B.Cu @ (8.65,27.80): pad1(W)=GND, pad2(E)=BOOST_FB
    R13 = 576k 0402 B.Cu @ (10.60,27.80): pad1(W)=BOOST_FB, pad2(E)=3V3_BAT
    -> VOUT nominal = 1.00 * (1 + 576/249) = 3.313V, divider ~4.0uA.
 2. B.Cu routing (w=0.15 unless noted): J3.6 GND jog chain to the J3.MP
    stub, BOOST_FB feed from the Phase 1 run to R14.2, R14.1 -> U3 EP.
 3. 3V3_BAT feed for R13.2: via @ (11.42,27.95) + F.Cu ride joining the
    existing F.Cu 3V3_BAT diagonal to C5.1.
 4. GND island bridge: Phase 1 cut J3.6's old GND feed, leaving
    {J3.6, jog, J3.MP, J4.MP} floating. A jumper resistor across the FB
    feed was measured impossible (0805/0603/0402: TB5 via (6.86,27.50)
    and 3V3 via (8.30,26.35) leave no pad window). The bridge instead
    runs on B.Cu from J4.MP south through the R13 pad gap (x=10.51,
    w=0.10; clearances R13.1 +0.100 / EX5 via +0.115), diagonally past
    the BOOST_SW via, then west at y=29.275 through the 0.30 gap
    between U3.4 (south edge 29.125) and U3.5 (north edge 29.425),
    w=0.10, into the U3 EP east edge (main GND).

Every element is clearance-checked with checker.py before being added
(pad_audit checks the new footprints' pads against all B.Cu copper).
Any FAIL aborts without saving. Acceptance after applying: DRC
(.kicad_pcb + .kicad_pro only, no .prl) unconnected 0, clearance 0,
shorting only the intentional SJ/JP joints, tracks_crossing unchanged.
Result on 2026-11-17: total 195-196 (shorting count wobbles 5/6, known
kicad-cli nondeterminism on the SJ1 joint), unconnected 0.
"""
import os, sys, math
import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import checker

BOARD = os.environ['BOARD_PATH']
LIB = os.path.expanduser(
    '~/workspace/tools-cache/kicad8-local/usr/share/kicad/footprints/'
    'Resistor_SMD.pretty')
mm = 1e6
BCu, FCu = pcbnew.B_Cu, pcbnew.F_Cu

b = pcbnew.LoadBoard(BOARD)
fails = []

def netcode(name):
    n = b.FindNet(name)
    assert n is not None, f'net {name} not found'
    return n.GetNetCode()

def add_seg(net, layer, x1, y1, x2, y2, w=0.15):
    ok, clr, desc = checker.check_seg(b, net, layer, x1, y1, x2, y2, w)
    print(f'SEG {net} L{layer} ({x1:.2f},{y1:.2f})->({x2:.2f},{y2:.2f}) '
          f'w={w}: clr={clr:.3f} {"PASS" if ok else "FAIL " + desc}')
    if not ok:
        fails.append(f'seg {net} ({x1},{y1})->({x2},{y2})')
        return
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(int(round(x1 * mm)), int(round(y1 * mm))))
    t.SetEnd(pcbnew.VECTOR2I(int(round(x2 * mm)), int(round(y2 * mm))))
    t.SetWidth(int(round(w * mm)))
    t.SetLayer(layer)
    t.SetNetCode(netcode(net))
    b.Add(t)

def add_via(net, x, y):
    ok, clr, desc = checker.check_via(b, net, x, y)
    print(f'VIA {net} ({x:.2f},{y:.2f}): clr={clr:.3f} '
          f'{"PASS" if ok else "FAIL " + desc}')
    if not ok:
        fails.append(f'via {net} ({x},{y})')
        return
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(int(round(x * mm)), int(round(y * mm))))
    v.SetDrill(int(round(0.25 * mm)))
    v.SetWidth(int(round(0.45 * mm)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(FCu, BCu)
    v.SetNetCode(netcode(net))
    b.Add(v)

def rect_rect_dist(a, c):
    dx = max(a[0] - c[2], c[0] - a[2], 0.0)
    dy = max(a[1] - c[3], c[1] - a[3], 0.0)
    return math.hypot(dx, dy)

def pad_rect(pad):
    bb = pad.GetBoundingBox()
    return (bb.GetX() / mm, bb.GetY() / mm,
            (bb.GetX() + bb.GetWidth()) / mm,
            (bb.GetY() + bb.GetHeight()) / mm)

def pad_audit(fp):
    tracks, vias, pads = checker._items(b)
    worst, wdesc = 9e9, ''
    for p in fp.Pads():
        r = pad_rect(p)
        net = p.GetNetname()
        for (n, l, a1, b1, c1, d1, tw) in tracks:
            if n == net or l != BCu:
                continue
            dist = checker._seg_rect_dist((a1, b1, c1, d1), r) - tw / 2
            if dist < worst:
                worst, wdesc = dist, f'track[{n}]@({a1:.2f},{b1:.2f})'
        for (n, vx, vy, vr) in vias:
            if n == net:
                continue
            dist = checker._rect_dist(vx, vy, *r) - vr
            if dist < worst:
                worst, wdesc = dist, f'via[{n}]@({vx:.2f},{vy:.2f})'
        for (n, opad, rx0, ry0, rx1, ry1) in pads:
            if opad is p or n == net:
                continue
            if BCu not in checker._pad_layers(opad):
                continue
            dist = rect_rect_dist(r, (rx0, ry0, rx1, ry1))
            if dist < worst:
                worst, wdesc = dist, (f'pad[{n}] '
                    f'{opad.GetParentFootprint().GetReference()}.'
                    f'{opad.GetNumber()}')
    ok = worst >= checker.REQ
    print(f'PAD_AUDIT {fp.GetReference()}: min clr={worst:.3f} '
          f'{"PASS" if ok else "FAIL"} worst={wdesc}')
    if not ok:
        fails.append(f'pad_audit {fp.GetReference()}')
    return worst

def add_fp(libname, ref, value, x, y, rot, padnets):
    fp = pcbnew.FootprintLoad(LIB, libname)
    b.Add(fp)  # Add BEFORE Flip (Flip->Add segfaults on some builds)
    fp.SetReference(ref)
    fp.SetValue(value)
    centre = pcbnew.VECTOR2I(int(round(x * mm)), int(round(y * mm)))
    fp.SetPosition(centre)
    fp.Flip(centre, False)
    if rot:
        fp.SetOrientationDegrees(rot)
    for p in fp.Pads():
        p.SetNetCode(netcode(padnets[p.GetNumber()]))
    for p in fp.Pads():
        pp = p.GetPosition()
        print(f'  {ref}.{p.GetNumber()} net={p.GetNetname()} '
              f'pos=({pp.x / mm:.3f},{pp.y / mm:.3f})')
    return fp

# ---- 0. J3.6 pad trim ----
j3 = [fp for fp in b.GetFootprints() if fp.GetReference() == 'J3'][0]
for p in j3.Pads():
    if p.GetNumber() == '6':
        pp = p.GetPosition()
        p.SetSize(pcbnew.VECTOR2I(int(round(0.30 * mm)),
                                  int(round(1.20 * mm))))
        p.SetPosition(pcbnew.VECTOR2I(pp.x, int(round(28.05 * mm))))
        print(f'J3.6 trimmed: pos=({pp.x / mm:.2f},28.05) size=0.30x1.20')

# ---- 1. divider footprints ----
r14 = add_fp('R_0402_1005Metric', 'R14', '249k', 8.65, 27.80, 0,
             {'1': 'GND', '2': 'BOOST_FB'})
r13 = add_fp('R_0402_1005Metric', 'R13', '576k', 10.60, 27.80, 0,
             {'1': 'BOOST_FB', '2': '3V3_BAT'})
for fp in (r14, r13):
    pad_audit(fp)

j36 = [p for p in j3.Pads() if p.GetNumber() == '6'][0]
u3 = [fp for fp in b.GetFootprints() if fp.GetReference() == 'U3'][0]
u33 = [p for p in u3.Pads() if p.GetNumber() == '3'][0]
d = rect_rect_dist(pad_rect(j36), pad_rect(u33))
print(f'J3.6<->U3.3 rect dist after trim: {d:.3f} '
      f'{"PASS" if d >= checker.REQ else "FAIL"}')
if d < checker.REQ:
    fails.append('J3.6<->U3.3 trim')

# ---- 2. B.Cu routing ----
add_seg('GND', BCu, 6.55, 28.05, 7.22, 28.05)
add_seg('GND', BCu, 7.22, 28.05, 7.22, 25.42, 0.10)
add_seg('GND', BCu, 7.22, 25.42, 7.47, 25.42)
add_seg('GND', BCu, 7.47, 25.42, 7.47, 25.68)
add_seg('BOOST_FB', BCu, 9.30, 27.80, 9.95, 27.80)
add_seg('BOOST_FB', BCu, 7.47, 26.90, 9.16, 26.90)
add_seg('BOOST_FB', BCu, 9.16, 26.90, 9.16, 27.95)
add_seg('GND', BCu, 8.05, 28.00, 8.05, 29.60)

# ---- 3. 3V3_BAT feed ----
add_via('3V3_BAT', 11.42, 27.95)
add_seg('3V3_BAT', FCu, 11.42, 27.95, 8.20, 27.95)
add_seg('3V3_BAT', FCu, 8.20, 27.95, 8.20, 31.55)
add_seg('3V3_BAT', FCu, 8.20, 31.55, 7.75, 31.90)
add_seg('3V3_BAT', FCu, 7.75, 31.90, 8.45, 32.60)
add_seg('3V3_BAT', FCu, 8.45, 32.60, 8.45, 34.20)
add_seg('3V3_BAT', FCu, 8.45, 34.20, 10.58, 34.20)

# ---- 4. GND island bridge ----
add_seg('GND', BCu, 10.51, 25.90, 10.51, 29.00, 0.10)
add_seg('GND', BCu, 10.51, 29.00, 10.10, 29.275, 0.10)
add_seg('GND', BCu, 10.10, 29.275, 8.05, 29.275, 0.10)

if fails:
    print('ABORT, not saving. FAILS:', fails)
    sys.exit(1)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(BOARD)
print('SAVED', BOARD)
