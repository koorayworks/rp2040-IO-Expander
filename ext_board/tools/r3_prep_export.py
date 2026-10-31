#!/usr/bin/env python3
"""Round-3 export prep: copy board, rip all non-GND routing, split SJ
jumper legs into pseudo-nets (so Freerouting cannot bypass the cuttable
necks), drop the 3 non-GND necks, remove rule-area zones in the copy only,
then export Specctra DSN."""
import pcbnew, os

SRC = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
TMPB = "/tmp/r3_export.kicad_pcb"
OUT = "/tmp/r3.dsn"

b = pcbnew.LoadBoard(SRC)

# Freerouting mis-associates DSN images whose footprint name is empty
# (KiCad exports "", "::1", "::2", "::3"); in round 3 run 1 the four SJ
# footprints silently received J6's 10-pin image and were routed at
# phantom positions ~x=24-27mm. Give every empty-named footprint a unique
# name in the EXPORT COPY ONLY (final board keeps its footprints).
named = []
for fp in b.GetFootprints():
    if not str(fp.GetFPID().GetLibItemName()):
        fp.SetFPID(pcbnew.LIB_ID("", "FP_" + fp.GetReference()))
        named.append(fp.GetReference())
print("unique FPIDs assigned in export copy:", named, flush=True)

def add_net(name):
    ni = pcbnew.NETINFO_ITEM(b, name)
    b.Add(ni)
    return ni

def set_pad_net(ref, num, net):
    fp = b.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            p.SetNet(net)
            return True
    raise RuntimeError(f"pad {ref}.{num} not found")

legs = {"SJ1L": (("J4", "1"), ("SJ1", "2")),
        "SJ3L": (("J4", "3"), ("SJ3", "2")),
        "SJ4L": (("J4", "4"), ("SJ4", "2")),
        "SJ6L": (("J4", "6"), ("SJ6", "2"))}
for lname, pads in legs.items():
    ni = add_net(lname)
    for ref, num in pads:
        set_pad_net(ref, num, ni)
# Freerouting derives the JLEG castellation pads' terminal point from
# their offset capsule shape and lands at anchor+1.95mm along the pad
# axis (outside the outline for edge pads), dragging spines off-board.
# Centre the pads on their anchors in the EXPORT COPY ONLY: same size
# (2.60x1.50) and drill, offset (0,0). The model stays conservative vs
# the real copper on every side that matters (see r3_progress.md).
jleg = b.FindFootprintByReference("JLEG")
n_centered = 0
for p in jleg.Pads():
    p.SetOffset(pcbnew.VECTOR2I(0, 0))
    n_centered += 1
print("JLEG pads centred in export copy:", n_centered, flush=True)

print("pseudo-nets assigned", flush=True)

# rip all non-GND tracks/vias (includes the SJ1/SJ3/SJ4 necks and feeds),
# plus GND items touching the SJ6L pads (its neck/stub) -- single pass,
# because a second GetTracks() call degrades in this SWIG build.
import math
targets = [(10.45, 20.55), (10.25, 15.65)]  # SJ6.2 centre, J4.6 centre
def touches_sj6l(t):
    pts = []
    if t.Type() == pcbnew.PCB_VIA_T:
        pp = t.GetPosition(); pts = [(pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y))]
    else:
        for fn in (t.GetStart, t.GetEnd):
            pp = fn(); pts.append((pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y)))
    return any(math.hypot(x - tx, y - ty) < 0.36 for x, y in pts for tx, ty in targets)
removed = 0
removed_gnd = 0
for t in list(b.GetTracks()):
    if t.GetNetname() != "GND":
        b.Remove(t); removed += 1
    elif touches_sj6l(t):
        b.Remove(t); removed_gnd += 1
print("ripped non-GND tracks/vias:", removed, flush=True)
print("removed GND items touching SJ6L pads:", removed_gnd, flush=True)

pcbnew.SaveBoard(TMPB, b)
ok = pcbnew.ExportSpecctraDSN(b, OUT)
print("DSN export:", ok, os.path.getsize(OUT) if os.path.exists(OUT) else "missing")
