import os, pcbnew
ROOT=os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC=os.path.join(ROOT,'split/module_board/backup/placement_v47_round52seeds.kicad_pcb')
OUT=os.path.join(ROOT,'split/module_board/module_board.kicad_pcb')
b=pcbnew.LoadBoard(SRC); mm=pcbnew.FromMM
NETS={}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n=pad.GetNet()
        if n and n.GetNetname(): NETS.setdefault(n.GetNetname(), n)
t=pcbnew.PCB_TRACK(b)
t.SetStart(pcbnew.VECTOR2I(mm(14.35),mm(15.7))); t.SetEnd(pcbnew.VECTOR2I(mm(14.35),mm(17.6)))
t.SetWidth(mm(0.15)); t.SetLayer(pcbnew.In2_Cu); t.SetNet(NETS['GPIO10']); b.Add(t)
pcbnew.SaveBoard(OUT,b); print('saved r66')
