#!/usr/bin/env python3
"""Prep B: targeted re-route of ONLY the four edge-overshoot nets
(GPIO2/3/4/7) on top of the verified w4 board. Everything else stays
as DSN wiring. Export copy gets: unique FPIDs for empty-named
footprints (SJ obstacle correctness) and centred JLEG pads (terminal
point = pad centre, so Freerouting no longer drags spines off-board).
Zones/rule areas are kept (KiCad writes planes/keepouts into the DSN).
"""
import pcbnew, os

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board")
SRC = os.path.join(BASE, "tools", "r3_work", "w4.kicad_pcb")
TMPB = os.path.join(BASE, "tools", "r3_work", "r3b_export.kicad_pcb")
OUT = os.path.join(BASE, "tools", "r3_work", "r3b.dsn")
TARGETS = {"GPIO2", "GPIO3", "GPIO4", "GPIO7"}

b = pcbnew.LoadBoard(SRC)
named = []
for fp in b.GetFootprints():
    if not str(fp.GetFPID().GetLibItemName()):
        fp.SetFPID(pcbnew.LIB_ID("", "FP_" + fp.GetReference()))
        named.append(fp.GetReference())
print("unique FPIDs:", named, flush=True)

jleg = b.FindFootprintByReference("JLEG")
for p in jleg.Pads():
    p.SetOffset(pcbnew.VECTOR2I(0, 0))
print("JLEG pads centred", flush=True)

removed = 0
for t in list(b.GetTracks()):
    if t.GetNetname() in TARGETS:
        b.Remove(t); removed += 1
print("ripped target nets:", removed, flush=True)

pcbnew.SaveBoard(TMPB, b)
ok = pcbnew.ExportSpecctraDSN(b, OUT)
print("DSN export:", ok, os.path.getsize(OUT) if os.path.exists(OUT) else "missing", flush=True)
