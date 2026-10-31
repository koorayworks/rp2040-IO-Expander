#!/usr/bin/env python3
"""Merge B: graft ONLY GPIO2/3/4/7 from the prep-B SES onto the w4
board (whose own copies of those nets are ripped first). All other
nets keep their w4 geometry byte-for-byte."""
import pcbnew, os, importlib.util

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board")
EXPORT = os.path.join(BASE, "tools", "r3_work", "r3b_export.kicad_pcb")
SES = os.path.join(BASE, "tools", "r3_work", "r3b.ses")
TARGET = os.path.join(BASE, "tools", "r3_work", "w4.kicad_pcb")
OUT = os.path.join(BASE, "tools", "r3_work", "w5.kicad_pcb")
TARGETS = {"GPIO2", "GPIO3", "GPIO4", "GPIO7"}

spec = importlib.util.spec_from_file_location("r3_ses_parse", os.path.join(BASE, "tools", "r3_ses_parse.py"))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
rb = pcbnew.LoadBoard(EXPORT)
stats, skipped, created = sp.build(rb, SES)
print("SES rebuilt; skipped:", dict(skipped), flush=True)

fb = pcbnew.LoadBoard(TARGET)
codes = {}
for fp in fb.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname():
            codes[p.GetNetname()] = p.GetNetCode()
ripped = 0
for t in list(fb.GetTracks()):
    if t.GetNetname() in TARGETS:
        fb.Remove(t); ripped += 1
print("ripped from w4:", ripped, flush=True)

added = 0
for n, t in created:
    if n not in TARGETS:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        nt = pcbnew.PCB_VIA(fb)
        nt.SetPosition(t.GetPosition())
        nt.SetDrill(t.GetDrillValue())
        nt.SetWidth(t.GetWidth())
        nt.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    else:
        nt = pcbnew.PCB_TRACK(fb)
        nt.SetStart(t.GetStart()); nt.SetEnd(t.GetEnd())
        nt.SetWidth(t.GetWidth()); nt.SetLayer(t.GetLayer())
    nt.SetNetCode(codes[n])
    fb.Add(nt); added += 1
print("grafted:", added, flush=True)

f = pcbnew.ZONE_FILLER(fb); print("fill:", f.Fill(fb.Zones()), flush=True)
pcbnew.SaveBoard(OUT, fb)
print("saved:", OUT, flush=True)
