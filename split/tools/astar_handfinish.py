import sys, math, heapq, pcbnew
sys.path.insert(0, '/home/hatch/workspace/projects/rp2040-IO-Expander/split/tools')
import checker as CK

import os
BOARD=os.environ.get('HF_BOARD','/tmp/hf_work.kicad_pcb')
b=pcbnew.LoadBoard(BOARD)
LAYERS=[pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu]
LN={pcbnew.F_Cu:'F',pcbnew.In1_Cu:'I1',pcbnew.In2_Cu:'I2',pcbnew.B_Cu:'B'}
tracks, vias, pads = CK._items(b)
pad_layers={id(p): CK._pad_layers(p) for (_,p,*_ ) in pads}
PADL={}
for (n,p,x0,y0,x1,y1) in pads: PADL[id(p)]=CK._pad_layers(p)
REQ=0.099; W=0.15

def seg_ok(net, layer, x1,y1,x2,y2):
    seg=(x1,y1,x2,y2)
    for (n,l,a,bb,c,d,tw) in tracks:
        if n==net or l!=layer: continue
        if max(a,c)<min(x1,x2)-0.6 or min(a,c)>max(x1,x2)+0.6: continue
        if max(bb,d)<min(y1,y2)-0.6 or min(bb,d)>max(y1,y2)+0.6: continue
        if CK._seg_seg_dist(seg,(a,bb,c,d)) - W/2 - tw/2 < REQ: return False
    for (n,vx,vy,r) in vias:
        if n==net: continue
        if abs(vx-x1)>8 or abs(vy-y1)>8: pass
        if CK._seg_pt_dist(vx,vy,x1,y1,x2,y2) - W/2 - r < REQ: return False
    for (n,p,rx0,ry0,rx1,ry1) in pads:
        if n==net or layer not in PADL[id(p)]: continue
        if CK._seg_rect_dist(seg,(rx0,ry0,rx1,ry1)) - W/2 < REQ: return False
    return True

def via_ok(net, x, y, r=0.20):
    for (n,l,a,bb,c,d,tw) in tracks:
        if n==net: continue
        if CK._seg_pt_dist(x,y,a,bb,c,d) - r - tw/2 < REQ: return False
    for (n,vx,vy,vr) in vias:
        if n==net: continue
        if math.hypot(x-vx,y-vy) - r - vr < REQ: return False
    for (n,p,rx0,ry0,rx1,ry1) in pads:
        if n==net: continue
        if CK._rect_dist(x,y,rx0,ry0,rx1,ry1) - r < REQ: return False
    return True

def net_elements(net):
    segs=[]; vs=[]; ps=[]
    for t in b.GetTracks():
        if t.GetNetname()!=net: continue
        if isinstance(t, pcbnew.PCB_VIA):
            p=t.GetPosition(); vs.append((p.x/1e6,p.y/1e6))
        else:
            s,e=t.GetStart(),t.GetEnd()
            segs.append((t.GetLayer(), s.x/1e6,s.y/1e6,e.x/1e6,e.y/1e6))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname()!=net: continue
            p=pad.GetPosition()
            ls=[l for l in LAYERS if pad.GetLayerSet().Contains(l)]
            ps.append((ls, p.x/1e6, p.y/1e6, f'{fp.GetReference()}.{pad.GetNumber()}'))
    return segs, vs, ps

def sample(segs, vs, ps, which):
    pts=[]
    for (l,x1,y1,x2,y2) in segs:
        if not which('seg',l,x1,y1): continue
        L=math.hypot(x2-x1,y2-y1); n=max(1,int(L/0.3))
        for i in range(n+1):
            pts.append((l, x1+(x2-x1)*i/n, y1+(y2-y1)*i/n))
    for (x,y) in vs:
        if not which('via',None,x,y): continue
        for l in LAYERS: pts.append((l,x,y))
    for (ls,x,y,name) in ps:
        if not which('pad',None,x,y): continue
        for l in ls: pts.append((l,x,y))
    return pts

def search(net, region, start_pts, goal_pts, step=0.2):
    x0,y0,x1,y1=region
    goals={}
    for (l,gx,gy) in goal_pts:
        goals.setdefault(l,[]).append((gx,gy))
    def is_goal(l,x,y):
        for (gx,gy) in goals.get(l,[]):
            if abs(gx-x)<0.01 and abs(gy-y)<0.01: return True
        return False
    # snap starts/goals to grid nodes list
    extra={}
    def add_node(l,x,y):
        extra[(l,round(x,3),round(y,3))]=True
    for (l,x,y) in start_pts+goal_pts: add_node(l,x,y)
    start_set=set((l,round(x,3),round(y,3)) for (l,x,y) in start_pts)
    goal_set=set((l,round(x,3),round(y,3)) for (l,x,y) in goal_pts)
    import heapq
    openh=[]; came={}; gs={}
    for s in start_set:
        gs[s]=0.0; heapq.heappush(openh,(0.0,s))
    DIRS=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
    via_cache={}
    def neighbors(node):
        l,x,y=node
        out=[]
        cand=[]
        for (dx,dy) in DIRS:
            cand.append((l, round(x+dx*step,3), round(y+dy*step,3)))
        for (l2,x2,y2) in extra:
            if l2==l and abs(x2-x)<=step*1.42 and abs(y2-y)<=step*1.42 and (x2,y2)!=(x,y):
                cand.append((l2,x2,y2))
        for c in cand:
            if not (x0-0.01<=c[1]<=x1+0.01 and y0-0.01<=c[2]<=y1+0.01): continue
            if seg_ok(net,l,x,y,c[1],c[2]):
                out.append((c, math.hypot(c[1]-x,c[2]-y)))
        # via moves
        key=(round(x,3),round(y,3))
        if key not in via_cache: via_cache[key]=via_ok(net,x,y)
        if via_cache[key]:
            for l2 in LAYERS:
                if l2!=l: out.append(((l2,x,y), 0.4))
        return out
    def h(node):
        l,x,y=node
        best=1e9
        for (gx,gy) in goals.get(l,[]):
            best=min(best, math.hypot(gx-x,gy-y))
        if best==1e9:
            for l2,gl in goals.items():
                for (gx,gy) in gl: best=min(best, math.hypot(gx-x,gy-y)+0.4)
        return best
    seen=0
    while openh:
        f,node=heapq.heappop(openh)
        if node in goal_set and node not in start_set:
            path=[node]
            while node in came:
                node=came[node]; path.append(node)
            return list(reversed(path)), gs[path[0]] if False else None
        if f>gs.get(node,1e18)+h(node)+1e-9: continue
        seen+=1
        if seen>200000: return None, 'budget'
        for (c,cost) in neighbors(node):
            ng=gs[node]+cost
            if ng<gs.get(c,1e18):
                gs[c]=ng; came[c]=node
                heapq.heappush(openh,(ng+h(c),c))
    return None,'no path'

def simplify(net, path):
    # path: list of (layer,x,y); split into per-layer runs, then greedy shortcut
    runs=[]
    cur=[path[0]]
    for p in path[1:]:
        if p[0]==cur[-1][0]: cur.append(p)
        else:
            runs.append(cur); runs.append([cur[-1], p]); cur=[p]
    runs.append(cur)
    out=[]
    for run in runs:
        if len(run)<=2: out.extend(run if not out else run[1:]); continue
        l=run[0][0]
        pts=[(x,y) for (_,x,y) in run]
        simp=[pts[0]]; i=0
        while i<len(pts)-1:
            j=len(pts)-1
            while j>i+1 and not seg_ok(net,l,pts[i][0],pts[i][1],pts[j][0],pts[j][1]): j-=1
            simp.append(pts[j]); i=j
        seg=[(l,x,y) for (x,y) in simp]
        out.extend(seg if not out else seg[1:])
    return out

if __name__=='__main__':
    net=sys.argv[1]
    cfg=eval(open(f'/tmp/astar_cfg_{net}.py').read())
    segs,vs,ps=net_elements(net)
    sp=sample(segs,vs,ps,cfg['start'])
    gp=sample(segs,vs,ps,cfg['goal'])
    print(f'{net}: starts={len(sp)} goals={len(gp)}')
    path,err=search(net, cfg['region'], sp, gp, step=cfg.get('step',0.2))
    if not path:
        print('NO PATH', err); sys.exit(0)
    simp=simplify(net,path)
    print('PATH nodes', len(path), 'simplified', len(simp))
    vias_out=[]
    prev=None
    for (l,x,y) in simp:
        if prev and prev[0]!=l: vias_out.append((prev[1],prev[2]))
        print(f'  {LN[l]} ({x:.2f},{y:.2f})')
        prev=(l,x,y)
    print('VIAS at', vias_out)
    # authoritative verify
    okall=True
    for i in range(len(simp)-1):
        l=simp[i][0]
        if simp[i+1][0]!=l: continue
        r=CK.check_seg(b,net,l,simp[i][1],simp[i][2],simp[i+1][1],simp[i+1][2])
        if not r[0]: okall=False; print('  VERIFY FAIL', simp[i], simp[i+1], r)
    for (x,y) in vias_out:
        r=CK.check_via(b,net,x,y)
        print('  via verify', (x,y), r[0], f'clr={r[1]:.3f}', r[2] if not r[0] else '')
    print('VERIFY', 'ALL OK (segs)' if okall else 'SEG FAIL')
