import pcbnew, math, heapq, sys
FM = pcbnew.FromMM; TM = pcbnew.ToMM
SRC = "backups/board_micro9.kicad_pcb"
b = pcbnew.LoadBoard(SRC)
LAYN = {pcbnew.F_Cu:0, pcbnew.In2_Cu:1, pcbnew.B_Cu:2}
LAYV = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
# ---------------- exact geometry ----------------
def pt_seg(px,py,x1,y1,x2,y2):
    dx,dy = x2-x1, y2-y1; L2 = dx*dx+dy*dy
    if L2==0: return math.hypot(px-x1,py-y1)
    t = max(0,min(1,((px-x1)*dx+(py-y1)*dy)/L2)); return math.hypot(px-(x1+t*dx), py-(y1+t*dy))
def seg_seg(a,b_,c,d):
    def o(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    d1,d2,d3,d4 = o(c,d,a), o(c,d,b_), o(a,b_,c), o(a,b_,d)
    if ((d1>0)!=(d2>0)) and ((d3>0)!=(d4>0)): return 0.0
    return min(pt_seg(a[0],a[1],c[0],c[1],d[0],d[1]), pt_seg(b_[0],b_[1],c[0],c[1],d[0],d[1]),
               pt_seg(c[0],c[1],a[0],a[1],b_[0],b_[1]), pt_seg(d[0],d[1],a[0],a[1],b_[0],b_[1]))
def pt_rect(px,py,r):
    dx = max(r[0]-px,0,px-r[2]); dy = max(r[1]-py,0,py-r[3]); return math.hypot(dx,dy)
def seg_rect(s,e,r):
    if pt_rect(s[0],s[1],r)==0 or pt_rect(e[0],e[1],r)==0: return 0.0
    cs = [(r[0],r[1]),(r[2],r[1]),(r[2],r[3]),(r[0],r[3])]
    return min(seg_seg(s,e,cs[i],cs[(i+1)%4]) for i in range(4))
# ---------------- board model ----------------
class Item: pass
items = []   # tracks/vias: dicts
pads = []
for t in b.GetTracks():
    a,c = t.GetStart(), t.GetEnd()
    if t.GetClass()=="PCB_VIA": items.append({"k":"V","net":t.GetNetname(),"x":TM(a.x),"y":TM(a.y)})
    elif t.GetLayer() in LAYN: items.append({"k":"T","net":t.GetNetname(),"l":LAYN[t.GetLayer()],"x1":TM(a.x),"y1":TM(a.y),"x2":TM(c.x),"y2":TM(c.y)})
for fp in b.GetFootprints():
    for pad in fp.Pads():
        bb = pad.GetBoundingBox(); cen = pad.GetPosition()
        lay = set()
        if pad.IsOnLayer(pcbnew.F_Cu): lay.add(0)
        if pad.IsOnLayer(pcbnew.B_Cu): lay.add(2)
        if not lay: continue
        dr = pad.GetDrillSize(); dr_r = TM(dr.x)/2 if dr.x>0 else 0.0
        pads.append({"net":pad.GetNetname(),"lay":lay,"rect":(TM(bb.GetLeft()),TM(bb.GetTop()),TM(bb.GetRight()),TM(bb.GetBottom())),"c":(TM(cen.x),TM(cen.y)),"dr":dr_r,"multi":pad.IsOnLayer(pcbnew.In2_Cu)})
def validate(cands, net):
    """cands: list of ('T',l,x1,y1,x2,y2) or ('V',x,y). Returns list of (cand_idx, desc, dist, req)."""
    bad = []
    for i,cd in enumerate(cands):
        for it in items:
            if it["net"]==net: continue
            if cd[0]=="T":
                _,l,x1,y1,x2,y2 = cd
                if it["k"]=="T":
                    if it["l"]!=l: continue
                    d = seg_seg((x1,y1),(x2,y2),(it["x1"],it["y1"]),(it["x2"],it["y2"])); req = 0.20
                    if d < req-1e-9: bad.append((i,f'Trk {it["net"]} L{it["l"]}',d,req))
                else:
                    d = pt_seg(it["x"],it["y"],x1,y1,x2,y2); req = 0.35
                    if d < req-1e-9: bad.append((i,f'Via {it["net"]}',d,req))
            else:
                _,x,y = cd
                if it["k"]=="T":
                    d = pt_seg(x,y,it["x1"],it["y1"],it["x2"],it["y2"]); req = 0.35
                    if d < req-1e-9: bad.append((i,f'Trk {it["net"]} L{it["l"]}',d,req))
                else:
                    d = math.hypot(x-it["x"],y-it["y"]); req = 0.50
                    if d < req-1e-9: bad.append((i,f'Via {it["net"]}',d,req))
        for pd in pads:
            if pd["net"]==net: continue
            if cd[0]=="T":
                _,l,x1,y1,x2,y2 = cd
                if pd["multi"] or l in pd["lay"]:
                    d = seg_rect((x1,y1),(x2,y2),pd["rect"]); req = 0.15
                    if d < req-1e-9: bad.append((i,f'Pad {pd["net"]}',d,req))
                if pd["dr"]>0:
                    d = min(pt_seg(pd["c"][0],pd["c"][1],x1,y1,x2,y2), 1e9); req = pd["dr"]+0.25
                    if d < req-1e-9: bad.append((i,f'PadHole {pd["net"]}',d,req))
            else:
                _,x,y = cd
                d = pt_rect(x,y,pd["rect"]); req = 0.30
                if d < req-1e-9: bad.append((i,f'Pad {pd["net"]}',d,req))
                if pd["dr"]>0:
                    d = math.hypot(x-pd["c"][0],y-pd["c"][1]); req = pd["dr"]+0.30
                    if d < req-1e-9: bad.append((i,f'PadHole {pd["net"]}',d,req))
    return bad
# ---------------- grid A* ----------------
G = 0.05; NX, NY = int(18.0/G)+1, int(43.5/G)+1
def seg_cells(x1,y1,x2,y2,r):
    out=set(); bx0,bx1 = min(x1,x2)-r, max(x1,x2)+r; by0,by1 = min(y1,y2)-r, max(y1,y2)+r
    dx,dy = x2-x1, y2-y1; L2 = dx*dx+dy*dy
    for cx in range(max(0,int(bx0/G)), min(NX-1,int(bx1/G))+1):
        for cy in range(max(0,int(by0/G)), min(NY-1,int(by1/G))+1):
            px,py = cx*G, cy*G
            t = max(0,min(1,((px-x1)*dx+(py-y1)*dy)/L2)) if L2 else 0
            if math.hypot(px-(x1+t*dx), py-(y1+t*dy)) <= r+1e-9: out.add((cx,cy))
    return out
def disc_cells(x,y,r):
    out=set()
    for cx in range(max(0,int((x-r)/G)), min(NX-1,int((x+r)/G))+1):
        for cy in range(max(0,int((y-r)/G)), min(NY-1,int((y+r)/G))+1):
            if math.hypot(cx*G-x, cy*G-y) <= r+1e-9: out.add((cx,cy))
    return out
def rect_cells(r,inf):
    out=set(); x0,y0,x1,y1 = r
    for cx in range(max(0,int((x0-inf)/G)), min(NX-1,int((x1+inf)/G))+1):
        for cy in range(max(0,int((y0-inf)/G)), min(NY-1,int((y1+inf)/G))+1):
            if pt_rect(cx*G,cy*G,r) <= inf+1e-9: out.add((cx,cy))
    return out
OFF = {"tt":0.17,"vt":0.32,"vv":0.47,"tp":0.12,"vp":0.27,"th":0.22,"vh":0.27}
def build_obstacles(net, extra_block):
    trk=[set(),set(),set()]; via=set()
    for it in items:
        if it["net"]==net: continue
        if it["k"]=="T":
            trk[it["l"]] |= seg_cells(it["x1"],it["y1"],it["x2"],it["y2"],OFF["tt"])
            via |= seg_cells(it["x1"],it["y1"],it["x2"],it["y2"],OFF["vt"])
        else:
            for l in range(3): trk[l] |= disc_cells(it["x"],it["y"],OFF["vt"])
            via |= disc_cells(it["x"],it["y"],OFF["vv"])
    for pd in pads:
        if pd["net"]==net: continue
        ls = range(3) if pd["multi"] else pd["lay"]
        for l in ls: trk[l] |= rect_cells(pd["rect"],OFF["tp"])
        via |= rect_cells(pd["rect"],OFF["vp"])
        if pd["dr"]>0:
            for l in range(3): trk[l] |= disc_cells(pd["c"][0],pd["c"][1],pd["dr"]+OFF["th"])
            via |= disc_cells(pd["c"][0],pd["c"][1],pd["dr"]+OFF["vh"])
    for l in range(3):
        for cx in range(NX):
            for cy in range(NY):
                x,y = cx*G, cy*G
                if x<0.30 or x>17.70 or y<0.30 or y>43.20: trk[l].add((cx,cy))
                if 4.35<=x<=13.65 and y>=37.90: trk[l].add((cx,cy))
    for (cx,cy,l) in extra_block: trk[l].add((cx,cy))
    for (cx,cy) in [(c[0],c[1]) for c in extra_block if c[2]==3]: via.add((cx,cy))
    return trk, via
def component_of(net, sx, sy):
    """union-find over net items+pads; return set of item indices in start component"""
    ni = [i for i,it in enumerate(items) if it["net"]==net]
    par = {i:i for i in ni}
    def find(a):
        while par[a]!=a: par[a]=par[par[a]]; a=par[a]
        return a
    def geom(it):
        return ("V",it["x"],it["y"]) if it["k"]=="V" else ("T",it["l"],it["x1"],it["y1"],it["x2"],it["y2"])
    def touch(a,b_):
        ga,gb = geom(a), geom(b_)
        if ga[0]=="V" and gb[0]=="V": return math.hypot(ga[1]-gb[1],ga[2]-gb[2]) <= 0.41
        if ga[0]=="V": return pt_seg(ga[1],ga[2],gb[2],gb[3],gb[4],gb[5]) <= 0.21 if gb[1]==gb[1] else False
        if gb[0]=="V": return pt_seg(gb[1],gb[2],ga[2],ga[3],ga[4],ga[5]) <= 0.21
        if ga[1]!=gb[1]: return False
        return seg_seg((ga[2],ga[3]),(ga[4],ga[5]),(gb[2],gb[3]),(gb[4],gb[5])) <= 0.11
    for ii in range(len(ni)):
        for jj in range(ii+1,len(ni)):
            if touch(items[ni[ii]], items[ni[jj]]):
                ra,rb = find(ni[ii]), find(ni[jj])
                if ra!=rb: par[ra]=rb
    # component containing an item within 0.3 of start
    start_root = None
    for i in ni:
        it = items[i]
        d = math.hypot(it["x"]-sx,it["y"]-sy) if it["k"]=="V" else pt_seg(sx,sy,it["x1"],it["y1"],it["x2"],it["y2"])
        if d <= 0.3: start_root = find(i); break
    if start_root is None: return set()
    return {i for i in ni if find(i)==start_root}
def target_cells(net, exclude_idx):
    tg=[set(),set(),set()]
    for i,it in enumerate(items):
        if it["net"]!=net or i in exclude_idx: continue
        if it["k"]=="T": tg[it["l"]] |= seg_cells(it["x1"],it["y1"],it["x2"],it["y2"],0.03)
        else:
            for l in range(3): tg[l] |= disc_cells(it["x"],it["y"],0.03)
    return tg
def astar(net, start, trk, via, tg, win):
    (sx,sy,sl) = start; x0,x1,y0,y1 = win
    cx0,cx1,cy0,cy1 = int(x0/G),int(x1/G),int(y0/G),int(y1/G)
    def h(cx,cy,l): return min((math.hypot(cx-tx,cy-ty) for (tx,ty) in tg[l]), default=1e9)
    startc = (int(round(sx/G)), int(round(sy/G)), sl)
    openh=[(0,startc)]; came={startc:None}; gs={startc:0.0}
    DIRS=[(1,0,1.0),(-1,0,1.0),(0,1,1.0),(0,-1,1.0),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]
    while openh:
        f,cur = heapq.heappop(openh); cx,cy,l = cur
        if (cx,cy) in tg[l] and cur!=startc:
            path=[]; c2=cur
            while c2: path.append(c2); c2=came[c2]
            return path[::-1]
        for (dx,dy,w) in DIRS:
            nx_,ny_ = cx+dx, cy+dy
            if not (cx0<=nx_<=cx1 and cy0<=ny_<=cy1): continue
            if (nx_,ny_) in trk[l]: continue
            if dx!=0 and dy!=0 and ((cx+dx,cy) in trk[l] or (cx,cy+dy) in trk[l]): continue
            nc=(nx_,ny_,l); ng=gs[cur]+w
            if ng < gs.get(nc,1e18): gs[nc]=ng; came[nc]=cur; heapq.heappush(openh,(ng+h(nx_,ny_,l),nc))
        for l2 in range(3):
            if l2==l or (cx,cy) in via: continue
            nc=(cx,cy,l2); ng=gs[cur]+6.0
            if ng < gs.get(nc,1e18): gs[nc]=ng; came[nc]=cur; heapq.heappush(openh,(ng+h(cx,cy,l2),nc))
    return None
def path_to_cands(path):
    pts=[(cx*G,cy*G,l) for (cx,cy,l) in path]
    cands=[]; run=[pts[0]]
    for p in pts[1:]:
        if p[2]!=run[-1][2]:
            cands.append(("RUN",run)); cands.append(("V",run[-1][0],run[-1][1])); run=[(run[-1][0],run[-1][1],p[2]),p]
        else: run.append(p)
    cands.append(("RUN",run))
    out=[]
    for cd in cands:
        if cd[0]=="V": out.append(("V",round(cd[1],2),round(cd[2],2))); continue
        run=cd[1]; comp=[run[0]]
        for i in range(1,len(run)-1):
            d1=(run[i][0]-comp[-1][0],run[i][1]-comp[-1][1]); d2=(run[i+1][0]-run[i][0],run[i+1][1]-run[i][1])
            if d1[0]*d2[1]-d1[1]*d2[0]!=0 or d1[0]*d2[0]+d1[1]*d2[1]<=0: comp.append(run[i])
        comp.append(run[-1])
        for i in range(len(comp)-1):
            (x1,y1,l),(x2,y2,_) = comp[i],comp[i+1]
            if x1==x2 and y1==y2: continue
            out.append(("T",l,round(x1,2),round(y1,2),round(x2,2),round(y2,2)))
    return out
def do_job(name, net, start, win):
    excl = component_of(net, start[0], start[1])
    tg = target_cells(net, excl)
    extra = set()
    for attempt in range(14):
        trk, via = build_obstacles(net, extra)
        path = astar(net, start, trk, via, tg, win)
        if path is None: print(name, "attempt", attempt, "NO PATH"); return False
        cands = path_to_cands(path)
        bad = validate(cands, net)
        if not bad:
            # emit
            for cd in cands:
                if cd[0]=="T":
                    _,l,x1,y1,x2,y2 = cd
                    t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(FM(x1),FM(y1))); t.SetEnd(pcbnew.VECTOR2I(FM(x2),FM(y2)))
                    t.SetWidth(FM(0.10)); t.SetLayer(LAYV[l]); t.SetNet(b.FindNet(net)); b.Add(t)
                    items.append({"k":"T","net":net,"l":l,"x1":x1,"y1":y1,"x2":x2,"y2":y2})
                else:
                    _,x,y = cd
                    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(FM(x),FM(y))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
                    v.SetDrill(FM(0.20)); v.SetWidth(FM(0.40)); v.SetNet(b.FindNet(net)); b.Add(v)
                    items.append({"k":"V","net":net,"x":x,"y":y})
            print(name, "OK attempt", attempt, "items:", len(cands)); return True
        # add penalty cells around violating candidates
        for (ci,desc,d,req) in bad:
            cd = cands[ci]
            if cd[0]=="T":
                _,l,x1,y1,x2,y2 = cd
                for (cx,cy) in seg_cells(x1,y1,x2,y2,0.10): extra.add((cx,cy,l))
            else:
                _,x,y = cd
                for l in range(3):
                    for (cx,cy) in disc_cells(x,y,0.10): extra.add((cx,cy,l))
        print(name, "attempt", attempt, "violations:", len(bad), bad[:3])
    print(name, "FAILED after attempts"); return False
JOBS = [
  ("STAIR","3V3_USB",(3.90,29.65,2),(3.0,5.6,28.6,32.2)),
  ("MODE2","3V3_USB",(3.00,30.30,2),(2.4,4.6,28.8,32.2)),
  ("VIN2","3V3_BAT",(3.50,29.56,2),(2.4,10.6,28.2,36.6)),
  ("PR1","PR1",(3.00,31.04,2),(2.2,6.8,29.0,37.9)),
  ("LEG","3V3_USB",(6.64,20.50,2),(2.2,11.5,18.5,37.9)),
]
for (nm,net,st,win) in JOBS: do_job(nm,net,st,win)
filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
b.Save(SRC); print("saved")
