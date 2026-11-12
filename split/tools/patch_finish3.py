import pcbnew
P = 'split/module_board/module_board.kicad_pcb'
b = pcbnew.LoadBoard(P)
def mm(v): return int(round(v * 1e6))
NETS = {}
for t in b.GetTracks():
    NETS[t.GetNet().GetNetname()] = t.GetNet()
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNet():
            NETS[p.GetNet().GetNetname()] = p.GetNet()
def track(x1, y1, x2, y2, layer, net_name):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(0.15))
    t.SetLayer(layer)
    t.SetNet(NETS[net_name])
    b.Add(t)
def via(x, y, net_name, dia=0.45, drill=0.25):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(dia))
    v.SetDrill(mm(drill))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(NETS[net_name])
    b.Add(v)
F, B, I1 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu
# 1. SJ4 join: trunk In2 endpoint (14.7,28.55) -> via -> B down to FFC2_4 island track
via(14.7, 28.55, '3V3')
track(14.7, 28.55, 14.7, 29.11, B, '3V3')
# 2. GPIO9 re-close on B from its own via (7.94,20.60); rip its In1 diagonal
track(7.94, 20.60, 9.6, 20.60, B, 'GPIO9')
track(9.6, 20.60, 9.6, 19.93, B, 'GPIO9')
removed = 0
for t in list(b.GetTracks()):
    if t.GetNet().GetNetname() != 'GPIO9' or t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() != I1: continue
    s, e = t.GetStart(), t.GetEnd()
    pts = {(round(s.x/1e6,2), round(s.y/1e6,2)), (round(e.x/1e6,2), round(e.y/1e6,2))}
    if pts == {(9.76,18.44),(7.94,20.26)} or pts == {(7.94,20.26),(7.94,20.60)}:
        b.Remove(t); removed += 1
print('GPIO9 In1 ripped:', removed)
# 3. GPIO7 via at (9.1,19.45) joining F chain to J2 pad16 B speck line
track(9.0, 19.45, 9.1, 19.45, F, 'GPIO7')
via(9.1, 19.45, 'GPIO7')
track(9.1, 19.45, 9.0, 19.85, B, 'GPIO7')
track(9.0, 19.85, 9.0, 19.93, B, 'GPIO7')
# 4. anchors for the router (frm13 seed)
track(12.9, 22.75, 13.6, 22.75, F, '3V3')      # D1: from J2 pad3 via island
track(6.9, 22.075, 6.9, 22.6, F, 'GPIO14')    # GPIO14 J1 pad9 stub
track(8.7, 22.075, 8.7, 21.5, F, 'GPIO8')     # GPIO8 J1 pad15 stub
track(5.1, 22.075, 5.25, 22.4, F, '3V3')      # 3V3 J1 pad3 stub
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(P, b)
print('saved patch_finish3')
