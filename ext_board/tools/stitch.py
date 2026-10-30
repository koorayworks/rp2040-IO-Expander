#!/usr/bin/env python3
"""GND stitching + zone setup/fill for the routed ext board.
- Adds GND zones on F.Cu, In1.Cu (plane), B.Cu (full-board rects).
- For every GND pad that is SMD (no drill), finds a nearby via spot using the
  Router6 grid model and drops a via + short stub track on the pad's layer.
- Fills zones and saves.
NOTE: needs the router stack (route2/3/4/6) importable; ROUTER_DIR env or
/tmp default."""
import pcbnew, os, math, sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["stitch"]
spec.loader.exec_module(rt)
MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

b = pcbnew.LoadBoard(PATH)
r = rt.R(b)
r.ingest()
# drop pre-existing copper zones (Stage A's In1 GND zone); keep rule areas
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Remove(z)
gnd = b.FindNet("GND")
gnd_id = r.net_ids["GND"]

def add_zone(layer, clearance=0.2):
    z = pcbnew.ZONE(b)
    z.SetNet(gnd)
    z.SetLayer(layer)
    z.SetMinThickness(MM(0.15))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetLocalClearance(MM(clearance))
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for (x, y) in [(0, 0), (18, 0), (18, 43.5), (0, 43.5)]:
        chain.Append(pcbnew.VECTOR2I(MM(x), MM(y)))
    chain.SetClosed(True)
    z.Outline().AddOutline(chain)
    b.Add(z)
    return z

for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu):
    add_zone(layer)

placed = []
failed = []
for fp in b.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetname() != "GND":
            continue
        if pad.GetDrillSize().x > 0:
            continue  # TH: zone connects directly
        ls = pad.GetLayerSet()
        if ls.Contains(pcbnew.F_Cu):
            L = 0
        elif ls.Contains(pcbnew.B_Cu):
            L = 2
        else:
            continue
        px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        done = False
        for rad in (0.7, 0.9, 1.1, 1.3, 1.6, 2.0):
            angs = [a * math.pi / 8 for a in range(16)]
            for a in angs:
                vx, vy = px + rad * math.cos(a), py + rad * math.sin(a)
                if not (0.5 <= vx <= 17.5 and 0.5 <= vy <= 43.0):
                    continue
                cx, cy = int(round(vx / 0.05)), int(round(vy / 0.05))
                vx, vy = cx * 0.05, cy * 0.05
                if not r.via_free(cy, cx, gnd_id):
                    continue
                steps = max(2, int(math.hypot(vx - px, vy - py) / 0.05))
                ok = True
                for i in range(steps + 1):
                    t = i / steps
                    sx, sy = px + (vx - px) * t, py + (vy - py) * t
                    ccx, ccy = int(round(sx / 0.05)), int(round(sy / 0.05))
                    if not r.track_free(L, ccy, ccx, gnd_id):
                        ok = False
                        break
                if not ok:
                    continue
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy)))
                v.SetWidth(MM(0.40))
                v.SetDrill(MM(0.20))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(gnd)
                b.Add(v)
                t2 = pcbnew.PCB_TRACK(b)
                t2.SetStart(pcbnew.VECTOR2I(MM(px), MM(py)))
                t2.SetEnd(pcbnew.VECTOR2I(MM(vx), MM(vy)))
                t2.SetWidth(MM(0.25))
                t2.SetLayer([pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu][L])
                t2.SetNet(gnd)
                b.Add(t2)
                r._stamp_via(vx, vy, gnd_id)
                r._stamp_track(L, (px, py), (vx, vy), gnd_id)
                r.rebuild_blockers()
                placed.append((fp.GetReference(), round(px, 2), round(py, 2), round(vx, 2), round(vy, 2)))
                done = True
                break
            if done:
                break
        if not done:
            failed.append((fp.GetReference(), round(px, 2), round(py, 2)))

print("stitch vias placed:", len(placed))
for p in placed:
    print("  ", p)
print("FAILED pads:", failed)
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(PATH, b)
print("STITCH DONE")
