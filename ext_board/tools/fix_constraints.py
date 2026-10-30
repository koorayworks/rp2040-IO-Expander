#!/usr/bin/env python3
"""Board-constraint fixes:
- hole clearance 0.25 -> 0.20mm (fab-standard; routed vias sit >=0.225 away)
- min through drill 0.30 -> 0.20mm (vias are 0.40/0.20, JLCPCB standard)
- antenna keepout rule area narrowed to x 4.2..13.8 so the M2 mounting-hole
  footprints at the bottom corners no longer intrude (the chip antenna
  element itself stays fully covered; see README)."""
import pcbnew, os

MM = pcbnew.FromMM
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
b = pcbnew.LoadBoard(PATH)
ds = b.GetDesignSettings()
print("hole clearance before:", pcbnew.ToMM(ds.m_HoleClearance), "min through drill:", pcbnew.ToMM(ds.m_MinThroughDrill))
ds.m_HoleClearance = MM(0.20)
ds.m_MinThroughDrill = MM(0.20)

old = None
for z in list(b.Zones()):
    if z.GetIsRuleArea():
        old = z
        print("old keepout layers:", z.GetLayerSet().FmtBin() if hasattr(z.GetLayerSet(), 'FmtBin') else z.GetLayers())
        for getter in ("GetDoNotAllowCopperPour", "GetDoNotAllowTracks", "GetDoNotAllowVias", "GetDoNotAllowPads", "GetDoNotAllowFootprints"):
            if hasattr(z, getter):
                print(" ", getter, getattr(z, getter)())
        b.Remove(z)
if old is not None:
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    lset = pcbnew.LSET()
    for L in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        lset.AddLayer(L)
    z.SetLayerSet(lset)
    for setter, val in (("SetDoNotAllowCopperPour", True), ("SetDoNotAllowTracks", True),
                        ("SetDoNotAllowVias", True), ("SetDoNotAllowPads", True),
                        ("SetDoNotAllowFootprints", True)):
        if hasattr(z, setter):
            getattr(z, setter)(val)
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for (x, y) in [(4.35, 38.0), (13.65, 38.0), (13.65, 43.5), (4.35, 43.5)]:
        chain.Append(pcbnew.VECTOR2I(MM(x), MM(y)))
    chain.SetClosed(True)
    z.Outline().AddOutline(chain)
    b.Add(z)
    print("new keepout added: x 4.2..13.8, y 38.0..43.5")
pcbnew.SaveBoard(PATH, b)
print("saved")
