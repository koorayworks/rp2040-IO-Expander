#!/usr/bin/env python3
"""Round-3 merge: import Freerouting SES into the export board, then graft
its non-GND routing onto the original board (which keeps its GND routing,
zones and rule areas). Pseudo-nets SJ1L/SJ3L/SJ4L map back to 3V3/EX3/EX4.
Finally re-add the 3 cuttable necks (B.Cu, w=0.20) exactly as designed."""
import pcbnew, os, sys

BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board")
EXPORT = sys.argv[3] if len(sys.argv) > 3 else "/tmp/r3_export.kicad_pcb"
SES = sys.argv[1] if len(sys.argv) > 1 else "/tmp/r3fr/r3.ses"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/r3_merged.kicad_pcb"
NETMAP = {"SJ1L": "3V3", "SJ3L": "EX3", "SJ4L": "EX4", "SJ6L": "GND"}

# 1) rebuild SES routing on the export board (custom parser)
import importlib.util
spec = importlib.util.spec_from_file_location("r3_ses_parse", os.path.join(BASE, "tools", "r3_ses_parse.py"))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
rb = pcbnew.LoadBoard(EXPORT)
stats, skipped, created = sp.build(rb, SES)
print("SES rebuild stats:", dict(stats), "skipped nets:", dict(skipped), flush=True)
pcbnew.SaveBoard("/tmp/r3_routed.kicad_pcb", rb)

# 2) load original, rip its non-GND routing
fb = pcbnew.LoadBoard(os.path.join(BASE, "ext_board.kicad_pcb"))
name2code = {}
for fp in fb.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname():
            name2code[p.GetNetname()] = p.GetNetCode()
ripped = 0
for t in list(fb.GetTracks()):
    if t.GetNetname() != "GND":
        fb.Remove(t)
        ripped += 1
print("ripped from final:", ripped, flush=True)

# 3) graft routed tracks/vias (skip GND: original GND geometry is kept)
added = 0
for n, t in created:
    if n == "GND":
        continue
    n = NETMAP.get(n, n)
    if n not in name2code:
        print("WARN: no net code for", n, flush=True)
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        nt = pcbnew.PCB_VIA(fb)
        nt.SetPosition(t.GetPosition())
        nt.SetDrill(t.GetDrillValue())
        nt.SetWidth(t.GetWidth())
        nt.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    else:
        nt = pcbnew.PCB_TRACK(fb)
        nt.SetStart(t.GetStart())
        nt.SetEnd(t.GetEnd())
        nt.SetWidth(t.GetWidth())
        nt.SetLayer(t.GetLayer())
    nt.SetNetCode(name2code[n])
    fb.Add(nt)
    added += 1
print("grafted tracks/vias:", added, flush=True)

# 4) re-add necks (B.Cu, width 0.20)
def add_neck(netname, x1, y1, x2, y2):
    tr = pcbnew.PCB_TRACK(fb)
    tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    tr.SetWidth(pcbnew.FromMM(0.20))
    tr.SetLayer(pcbnew.B_Cu)
    tr.SetNetCode(name2code[netname])
    fb.Add(tr)
add_neck("3V3", 7.75, 16.95, 8.70, 16.95)   # SJ1
add_neck("EX3", 8.15, 18.15, 8.40, 18.15)   # SJ3
add_neck("EX4", 8.65, 19.35, 8.95, 19.35)   # SJ4
print("necks re-added", flush=True)

pcbnew.SaveBoard(OUT, fb)
print("saved:", OUT, flush=True)
