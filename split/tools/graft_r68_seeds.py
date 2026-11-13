import os, pcbnew
ROOT=os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC=os.path.join(ROOT,'split/module_board/backup/placement_v59_round67seeds.kicad_pcb')
OUT=os.path.join(ROOT,'split/module_board/module_board.kicad_pcb')
b=pcbnew.LoadBoard(SRC); mm=pcbnew.FromMM
NETS={}
for fp in b.GetFootprints():
    for pad in fp.Pads():
        n=pad.GetNet()
        if n and n.GetNetname(): NETS.setdefault(n.GetNetname(), n)
def seg(net,layer,x1,y1,x2,y2):
    t=pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(x1),mm(y1))); t.SetEnd(pcbnew.VECTOR2I(mm(x2),mm(y2)))
    t.SetWidth(mm(0.15)); t.SetLayer(layer); t.SetNet(NETS[net]); b.Add(t)
def via40(net,x,y):
    v=pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x),mm(y)))
    v.SetWidth(mm(0.40)); v.SetDrill(mm(0.20)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(NETS[net]); b.Add(v)
F=pcbnew.F_Cu; I1=pcbnew.In1_Cu
# GPIO7 north seed (U1-side, unchanged coords)
seg('GPIO7',F,9.8,17.363,9.787,15.285); seg('GPIO7',F,9.787,15.285,10.659,14.413); seg('GPIO7',F,10.659,14.413,10.659,14.207); via40('GPIO7',10.659,14.207)
# GPIO6 anchor north extension (restore reach on shifted anchor)
seg('GPIO6',I1,10.1,18.7,10.1,18.2)
# GPIO28 F stub set (shifted +0.5)
seg('GPIO28',F,5.7,22.575,5.55,22.0); seg('GPIO28',F,5.55,22.0,6.2,22.0)
pcbnew.SaveBoard(OUT,b); print('saved r68 placement')
