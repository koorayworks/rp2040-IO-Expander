import pcbnew, math, heapq, sys
FM = pcbnew.FromMM; TM = pcbnew.ToMM
SRC = "backups/board_fix19state.kicad_pcb"
DST = "backups/board_micro9.kicad_pcb"
b = pcbnew.LoadBoard(SRC)
LAYN = {pcbnew.F_Cu:0, pcbnew.In2_Cu:1, pcbnew.B_Cu:2}
LAYV = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
# ---------- removals (fix20 removal sets) ----------
LAYR = {"F":pcbnew.F_Cu,"I2":pcbnew.In2_Cu,"B":pcbnew.B_Cu}
REM=set()
def R(net,lay,x1,y1,x2,y2): REM.add((net,lay,x1,y1,x2,y2)); REM.add((net,lay,x2,y2,x1,y1))
def RV(net,x,y): REM.add((net,"VIA",x,y))
for s in [(6.64,20.20,7.90,20.22),(7.90,20.22,8.15,21.75),(8.15,21.75,8.40,22.10),(8.40,22.10,9.00,23.70),(9.00,23.70,9.00,26.40),(9.00,26.40,6.45,26.35),(6.45,26.35,6.55,26.85),(6.55,26.85,6.55,28.15),(6.55,28.15,5.65,32.40)]: R("3V3_USB","B",*s)
R("3V3_USB","I2",5.65,32.40,6.20,34.45); R("3V3_USB","I2",6.20,34.45,5.65,36.60); R("3V3_USB","I2",5.65,36.60,5.58,36.15); RV("3V3_USB",5.65,32.40)
R("3V3_USB","B",7.90,35.88,8.35,36.30); R("3V3_USB","B",8.35,36.30,8.35,37.75); R("3V3_USB","B",8.35,37.75,7.30,37.85); R("3V3_USB","I2",7.30,37.85,6.25,36.15); RV("3V3_USB",7.30,37.85)
R("3V3_USB","B",3.66,30.86,3.94,30.36); R("3V3_USB","B",3.94,30.36,4.45,30.54)
R("3V3","B",3.85,29.71,3.79,30.51); R("3V3","B",3.79,30.51,3.92,31.15)
R("3V3","B",3.02,31.92,3.24,31.80); R("3V3","B",3.24,31.80,3.92,31.38)
for s in [(3.50,29.56,3.50,28.86),(3.50,28.86,3.18,28.30),(3.35,27.45,4.60,26.80),(4.60,26.80,5.45,27.02),(5.45,27.02,6.22,27.38)]: R("3V3_BAT","B",*s)
R("3V3_BAT","I2",3.18,28.30,3.35,27.45); R("3V3_BAT","I2",6.22,27.38,6.90,27.85); R("3V3_BAT","I2",6.90,27.85,7.00,28.75); R("3V3_BAT","I2",7.00,28.75,7.20,30.05); R("3V3_BAT","I2",7.20,30.05,8.75,31.55); R("3V3_BAT","I2",8.75,31.55,8.70,31.50)
RV("3V3_BAT",3.18,28.30); RV("3V3_BAT",3.35,27.45); RV("3V3_BAT",6.22,27.38)
R("PR1","B",2.85,31.04,2.98,31.40); R("PR1","F",2.98,31.40,2.48,32.85); R("PR1","B",2.48,32.85,2.90,32.75); R("PR1","B",2.90,32.75,3.58,33.15); R("PR1","B",3.58,33.15,3.58,34.15); R("PR1","B",3.58,34.15,3.98,34.72); R("PR1","B",3.98,34.72,4.12,35.35); R("PR1","B",4.12,35.35,4.95,35.50); R("PR1","B",4.95,35.50,4.60,35.85)
RV("PR1",2.98,31.40); RV("PR1",2.48,32.85)
R("3V3_USB","B",3.90,29.65,4.05,29.80); R("3V3_USB","B",4.05,29.80,4.20,29.95); R("3V3_USB","B",4.20,29.95,4.20,30.00); R("3V3_USB","B",4.20,30.00,4.25,30.05)
R("3V3_USB","B",2.90,30.30,3.35,30.75)
found=[]
for t in list(b.GetTracks()):
    a,c = t.GetStart(), t.GetEnd()
    if t.GetClass()=="PCB_VIA":
        if (t.GetNetname(),"VIA",round(TM(a.x),2),round(TM(a.y),2)) in REM: found.append(t)
    else:
        lr = {pcbnew.F_Cu:"F",pcbnew.In2_Cu:"I2",pcbnew.B_Cu:"B"}.get(t.GetLayer())
        if lr and (t.GetNetname(),lr,round(TM(a.x),2),round(TM(a.y),2),round(TM(c.x),2),round(TM(c.y),2)) in REM: found.append(t)
print("removals:", len(found), "expected >= 44")
for t in found: b.Remove(t)
# ---------- obstacle model ----------
G = 0.05
NX, NY = int(18.0/G)+1, int(43.5/G)+1
def cell(x,y): return (int(round(x/G)), int(round(y/G)))
def seg_cells(x1,y1,x2,y2,r):
    # cells whose center is within r of segment
    out=set()
    bx0,bx1 = min(x1,x2)-r, max(x1,x2)+r; by0,by1 = min(y1,y2)-r, max(y1,y2)+r
    dx,dy = x2-x1, y2-y1; L2 = dx*dx+dy*dy
    for cx in range(max(0,int(bx0/G)), min(NX-1,int(bx1/G))+1):
        for cy in range(max(0,int(by0/G)), min(NY-1,int(by1/G))+1):
            px,py = cx*G, cy*G
            if L2==0: d = math.hypot(px-x1,py-y1)
            else:
                t = max(0,min(1,((px-x1)*dx+(py-y1)*dy)/L2)); d = math.hypot(px-(x1+t*dx), py-(y1+t*dy))
            if d <= r+1e-9: out.add((cx,cy))
    return out
def disc_cells(x,y,r):
    out=set()
    for cx in range(max(0,int((x-r)/G)), min(NX-1,int((x+r)/G))+1):
        for cy in range(max(0,int((y-r)/G)), min(NY-1,int((y+r)/G))+1):
            if math.hypot(cx*G-x, cy*G-y) <= r+1e-9: out.add((cx,cy))
    return out
def rect_cells(x0,y0,x1,y1,inf):
    out=set()
    for cx in range(max(0,int((x0-inf)/G)), min(NX-1,int((x1+inf)/G))+1):
        for cy in range(max(0,int((y0-inf)/G)), min(NY-1,int((y1+inf)/G))+1):
            px,py = cx*G, cy*G
            dx = max(x0-px, 0, px-x1); dy = max(y0-py, 0, py-y1)
            if math.hypot(dx,dy) <= inf+1e-9: out.add((cx,cy))
    return out
# per-net copper target cells; global obstacle structures keyed by net to exclude
tracks_by_net = {}
vias_by_net = {}
pads = []  # (net, layers_set, rect, center, drill_r)
for t in b.GetTracks():
    a,c = t.GetStart(), t.GetEnd()
    if t.GetClass()=="PCB_VIA": vias_by_net.setdefault(t.GetNetname(),[]).append((TM(a.x),TM(a.y)))
    else:
        if t.GetLayer() in LAYN: tracks_by_net.setdefault(t.GetNetname(),[]).append((LAYN[t.GetLayer()],TM(a.x),TM(a.y),TM(c.x),TM(c.y)))
for fp in b.GetFootprints():
    for pad in fp.Pads():
        bb = pad.GetBoundingBox(); cen = pad.GetPosition()
        lay = set()
        if pad.IsOnLayer(pcbnew.F_Cu): lay.add(0)
        if pad.IsOnLayer(pcbnew.B_Cu): lay.add(2)
        if not lay: continue
        dr = pad.GetDrillSize(); dr_r = TM(dr.x)/2 if dr.x>0 else 0.0
        pads.append((pad.GetNetname(), lay, (TM(bb.GetLeft()),TM(bb.GetTop()),TM(bb.GetRight()),TM(bb.GetBottom())), (TM(cen.x),TM(cen.y)), dr_r, pad.IsOnLayer(pcbnew.In2_Cu)))
def build_obstacles(net):
    trk = [set(),set(),set()]   # blocked cells for MY track, per layer
    via = set()                  # blocked cells for MY via (any layer)
    for n,segs in tracks_by_net.items():
        if n==net: continue
        for (l,x1,y1,x2,y2) in segs:
            trk[l] |= seg_cells(x1,y1,x2,y2,0.20)
            via |= seg_cells(x1,y1,x2,y2,0.35)
    for n,vs in vias_by_net.items():
        if n==net: continue
        for (x,y) in vs:
            for l in range(3): trk[l] |= disc_cells(x,y,0.35)
            via |= disc_cells(x,y,0.50)
    for (n,lay,rect,cen,dr_r,pth) in pads:
        if n==net: continue
        ls = range(3) if pth else lay
        for l in ls: trk[l] |= rect_cells(*rect,0.15)
        via |= rect_cells(*rect,0.30)
        if dr_r>0:
            for l in range(3): trk[l] |= disc_cells(cen[0],cen[1],dr_r+0.25)
            via |= disc_cells(cen[0],cen[1],dr_r+0.30)
    # board edge + antenna keepout
    for l in range(3):
        for cx in range(NX):
            for cy in range(NY):
                x,y = cx*G, cy*G
                if x<0.30 or x>17.70 or y<0.30 or y>43.20: trk[l].add((cx,cy))
                if 4.35<=x<=13.65 and y>=37.90: trk[l].add((cx,cy))
    for cx in range(NX):
        for cy in range(NY):
            x,y = cx*G, cy*G
            if x<0.30 or x>17.70 or y<0.30 or y>43.20: via.add((cx,cy))
            if 4.35<=x<=13.65 and y>=37.90: via.add((cx,cy))
    return trk, via
def target_cells(net):
    tg = [set(),set(),set()]
    for (l,x1,y1,x2,y2) in tracks_by_net.get(net,[]):
        tg[l] |= seg_cells(x1,y1,x2,y2,0.03)
    for (x,y) in vias_by_net.get(net,[]):
        for l in range(3): tg[l] |= disc_cells(x,y,0.03)
    return tg
def astar(net, start, trk, via, tg, win):
    (sx,sy,sl) = start
    x0,x1,y0,y1 = win
    cx0,cx1,cy0,cy1 = int(x0/G),int(x1/G),int(y0/G),int(y1/G)
    def h(cx,cy,l):
        return min((math.hypot(cx-tx,cy-ty) for (tx,ty) in tg[l]), default=1e9)
    startc = (int(round(sx/G)), int(round(sy/G)), sl)
    openh = [(0, startc)]; came = {startc: None}; gs = {startc: 0.0}
    DIRS = [(1,0,1.0),(-1,0,1.0),(0,1,1.0),(0,-1,1.0),(1,1,1.414),(1,-1,1.414),(-1,1,1.414),(-1,-1,1.414)]
    goal = None
    while openh:
        f,cur = heapq.heappop(openh)
        cx,cy,l = cur
        if (cx,cy) in tg[l] and cur != startc: goal = cur; break
        if gs.get(cur,1e18) < f - h(cx,cy,l) - 1e-6: pass
        for (dx,dy,w) in DIRS:
            nx_,ny_ = cx+dx, cy+dy
            if not (cx0<=nx_<=cx1 and cy0<=ny_<=cy1): continue
            if (nx_,ny_) in trk[l]: continue
            nc = (nx_,ny_,l); ng = gs[cur]+w
            if ng < gs.get(nc,1e18): gs[nc]=ng; came[nc]=cur; heapq.heappush(openh,(ng+h(nx_,ny_,l), nc))
        for l2 in range(3):
            if l2==l: continue
            if (cx,cy) in via: continue
            nc = (cx,cy,l2); ng = gs[cur]+6.0
            if ng < gs.get(nc,1e18): gs[nc]=ng; came[nc]=cur; heapq.heappush(openh,(ng+h(cx,cy,l2), nc))
    if goal is None: return None
    path=[]; cur=goal
    while cur: path.append(cur); cur = came[cur]
    path.reverse(); return path
def emit(net, path):
    # compress to segments per layer run; vias at layer changes
    pts = [(cx*G, cy*G, l) for (cx,cy,l) in path]
    segs=[]; vias=[]
    run = [pts[0]]
    for p in pts[1:]:
        if p[2] != run[-1][2]:
            segs.append(run); vias.append((run[-1][0], run[-1][1])); run=[(run[-1][0],run[-1][1],p[2]), p]
        else: run.append(p)
    segs.append(run)
    out_items=[]
    for run in segs:
        # compress collinear
        comp=[run[0]]
        for i in range(1,len(run)-1):
            d1 = (run[i][0]-comp[-1][0], run[i][1]-comp[-1][1]); d2 = (run[i+1][0]-run[i][0], run[i+1][1]-run[i][1])
            if d1[0]*d2[1]-d1[1]*d2[0] != 0 or d1[0]*d2[0]+d1[1]*d2[1] <= 0: comp.append(run[i])
        comp.append(run[-1])
        for i in range(len(comp)-1):
            (x1,y1,l),(x2,y2,_) = comp[i], comp[i+1]
            if x1==x2 and y1==y2: continue
            t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(FM(round(x1,2)),FM(round(y1,2)))); t.SetEnd(pcbnew.VECTOR2I(FM(round(x2,2)),FM(round(y2,2))))
            t.SetWidth(FM(0.10)); t.SetLayer(LAYV[l]); t.SetNet(b.FindNet(net)); b.Add(t); out_items.append(("T",net,l,x1,y1,x2,y2))
            tracks_by_net.setdefault(net,[]).append((l,x1,y1,x2,y2))
    for (x,y) in vias:
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(FM(round(x,2)),FM(round(y,2)))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetDrill(FM(0.20)); v.SetWidth(FM(0.40)); v.SetNet(b.FindNet(net)); b.Add(v); out_items.append(("V",net,x,y))
        vias_by_net.setdefault(net,[]).append((x,y))
    return out_items
JOBS = [
  ("VIN1", "3V3_USB", (3.50,31.04,2), (2.6,5.2,28.6,32.4)),
  ("MODE", "3V3_USB", (3.00,29.56,2), (2.2,5.2,28.6,32.4)),
  ("LEG",  "3V3_USB", (6.64,20.50,2), (2.2,11.5,18.5,37.9)),
  ("R4L",  "3V3_USB", (7.60,35.48,2), (5.0,9.5,33.5,37.9)),
  ("STAIR","3V3_USB", (3.90,29.65,2), (3.2,5.2,28.8,31.6)),
  ("VOUT7","3V3", (4.00,29.56,2), (2.6,5.6,28.4,33.2)),
  ("VOUT2","3V3", (4.00,31.04,2), (2.6,5.6,28.4,33.2)),
  ("VIN2", "3V3_BAT", (3.50,29.56,2), (2.6,10.5,28.4,36.5)),
  ("PR1",  "PR1", (3.00,31.04,2), (2.2,6.6,29.0,37.9)),
]
for (name,net,start,win) in JOBS:
    trk, via = build_obstacles(net)
    tg = target_cells(net)
    # start cell must not be blocked by own pad: clear start neighborhood in trk (own-net pad excluded already since pads list includes U4 pads of this net -> excluded) OK
    path = astar(net, start, trk, via, tg, win)
    if path is None: print(name, "NO PATH"); continue
    items = emit(net, path)
    print(name, "routed:", len(items), "items, path cells:", len(path))
filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
b.Save(DST); print("saved", DST)
