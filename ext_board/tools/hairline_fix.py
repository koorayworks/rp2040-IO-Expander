import pcbnew, sys, math
PATH="/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb"
MM=pcbnew.FromMM
NAME=sys.argv[1]
b=pcbnew.LoadBoard(PATH)
LNAME={pcbnew.F_Cu:"F",pcbnew.In2_Cu:"In2",pcbnew.B_Cu:"B"}
tracks=[t for t in b.GetTracks() if t.GetNetname()==NAME]
def pt(q): return (pcbnew.ToMM(q.x),pcbnew.ToMM(q.y))
ends=[]  # (x,y,layer)
segs=[]  # (x1,y1,x2,y2,layer)
for t in tracks:
    if t.GetClass()=="PCB_VIA":
        x,y=pt(t.GetPosition()); ends.append((x,y,None))
    else:
        a=pt(t.GetStart()); c=pt(t.GetEnd()); lay=t.GetLayer()
        ends.append((a[0],a[1],lay)); ends.append((c[0],c[1],lay))
        segs.append((a[0],a[1],c[0],c[1],lay))
def seg_hits_bbox(s,bb):
    x1,y1,x2,y2,_=s
    for fx in (0.0,0.25,0.5,0.75,1.0):
        x=x1+(x2-x1)*fx; y=y1+(y2-y1)*fx
        if bb[0]-0.02<=x<=bb[2]+0.02 and bb[1]-0.02<=y<=bb[3]+0.02: return True
    return False
fixed=0
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname()!=NAME: continue
        bb=p.GetBoundingBox()
        bb=(pcbnew.ToMM(bb.GetLeft()),pcbnew.ToMM(bb.GetTop()),pcbnew.ToMM(bb.GetRight()),pcbnew.ToMM(bb.GetBottom()))
        px,py=pt(p.GetPosition())
        conn=False
        for (x,y,lay) in ends:
            if lay is None and bb[0]<=x<=bb[2] and bb[1]<=y<=bb[3]: conn=True; break
        if not conn:
            for s in segs:
                # layer must include pad layers: approx accept if seg layer in pad layers or pad is PTH
                if seg_hits_bbox(s,bb): conn=True; break
        if conn: continue
        # find nearest endpoint
        best=None
        for (x,y,lay) in ends:
            d=math.hypot(x-px,y-py)
            if best is None or d<best[0]: best=(d,x,y,lay)
        if best and best[0]<3.0:
            d,x,y,lay=best
            layer=lay if lay is not None else pcbnew.F_Cu
            # if pad is single-layer B and endpoint layer is F/In2, still add on endpoint layer + via at pad? keep simple: use endpoint layer; PTH ok; B pad with F endpoint won't connect -> skip those
            padlayers=[l for l in (pcbnew.F_Cu,pcbnew.In2_Cu,pcbnew.B_Cu) if p.IsOnLayer(l)]
            if len(padlayers)==1 and layer!=padlayers[0]:
                # add segment on pad layer from a via placed at endpoint
                v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x),MM(y)))
                v.SetWidth(MM(0.40)); v.SetDrill(MM(0.20)); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetNet(b.FindNet(NAME)); b.Add(v)
                layer=padlayers[0]
            t=pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(MM(x),MM(y))); t.SetEnd(pcbnew.VECTOR2I(MM(px),MM(py)))
            t.SetWidth(MM(0.10)); t.SetLayer(layer); t.SetNet(b.FindNet(NAME)); b.Add(t)
            fixed+=1
            print(f"fixed pad ({px:.2f},{py:.2f}) from ({x:.2f},{y:.2f}) d={d:.2f}")
print("fixed",fixed)
pcbnew.SaveBoard(PATH,b)
