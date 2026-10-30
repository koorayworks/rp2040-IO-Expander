import pcbnew, os
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
zones = list(b.Zones())          # collect BEFORE any Remove (KiCad quirk)
tracks = list(b.GetTracks())     # same
REMOVE = {(12.6, 1.55), (5.4, 1.55), (9.9, 11.05)}
n = 0
for t in tracks:
    if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND":
        p = t.GetPosition()
        key = (round(pcbnew.ToMM(p.x), 2), round(pcbnew.ToMM(p.y), 2))
        if key in REMOVE:
            b.Remove(t)
            n += 1
            print("removed stitch via at", key)
print("removed:", n)
for z in zones:
    if not z.GetIsRuleArea():
        try:
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_REMOVE)
            print("island removal set:", z.GetLayerName())
        except Exception as e:
            print("island mode failed:", e)
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(zones)
pcbnew.SaveBoard(PATH, b)
print("FIX_STITCH DONE")
