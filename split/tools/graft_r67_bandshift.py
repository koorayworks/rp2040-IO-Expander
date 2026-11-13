import os, pcbnew
ROOT=os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC=os.path.join(ROOT,'split/module_board/backup/placement_v43_round48seeds.kicad_pcb')
OUT=os.path.join(ROOT,'split/module_board/module_board.kicad_pcb')
b=pcbnew.LoadBoard(SRC); mm=pcbnew.FromMM
DY=0.5
STAY={'U1','U3','U4','L1','C1','C2','C4','C5','C6','C10','C11','SJ1','SJ3','SJ4','SJ6','J5','J6','H1','H2','H3','H4'}
def pt(v): return (round(v.x/1e6,4), round(v.y/1e6,4))
def key2(p): return (round(p[0],2), round(p[1],2))
# touch counts BEFORE (per pad: elements whose endpoint lies in pad rect)
def touch_counts(board):
    counts={}
    els=[]
    for t in board.GetTracks():
        if isinstance(t,pcbnew.PCB_VIA): els.append([pt(t.GetPosition())])
        else: els.append([pt(t.GetStart()), pt(t.GetEnd())])
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            p=pt(pad.GetPosition()); sz=pad.GetSize()
            rect=(p[0]-sz.x/2e6, p[1]-sz.y/2e6, p[0]+sz.x/2e6, p[1]+sz.y/2e6)
            c=sum(1 for e in els if any(rect[0]<=q[0]<=rect[2] and rect[1]<=q[1]<=rect[3] for q in e))
            counts[f"{fp.GetReference()}.{pad.GetNumber()}"]=c
    return counts
before=touch_counts(b)
move_fps=[]; seed_pads=set()
for fp in b.GetFootprints():
    ref=fp.GetReference(); pads=list(fp.Pads())
    if not pads: continue
    pts=[pt(p.GetPosition()) for p in pads]
    meany=sum(p[1] for p in pts)/len(pts)
    if ref in ('J1','J2') or (meany>=22.0 and ref not in STAY):
        move_fps.append(ref); seed_pads.update(pts)
        p=fp.GetPosition(); fp.SetPosition(pcbnew.VECTOR2I(p.x, p.y+mm(DY)))
print('moving footprints:', sorted(move_fps))
tracks=list(b.GetTracks())
def ends(t):
    if isinstance(t,pcbnew.PCB_VIA): return [pt(t.GetPosition())]
    return [pt(t.GetStart()), pt(t.GetEnd())]
sel=set(i for i,t in enumerate(tracks) if any(e in seed_pads for e in ends(t)))
changed=True
while changed:
    changed=False
    pts=set()
    for i in sel: pts.update(ends(tracks[i]))
    for i,t in enumerate(tracks):
        if i not in sel and any(e in pts for e in ends(t)): sel.add(i); changed=True
# explicit extra elements (net, is_via, endpoint key set)
EXTRA=[('3V3',False,{(6.66,25.85),(8.3,25.85)}),
       ('3V3',True,{(8.3,25.85)}),
       ('3V3',False,{(7.7,25.85),(8.3,25.85)}),
       ('EX5',False,{(10.9,25.79),(10.9,26.15)}),
       ('EX5',True,{(10.9,25.79)}),
       ('EX5',False,{(10.9,25.79),(12.6,25.8)}),
       ('EX5',False,{(12.6,25.8),(13.88,25.8)}),
       ('EX5',False,{(13.88,25.74),(13.9,27.6)}),
       ('GPIO1',False,{(10.8,19.6),(10.65,18.9)})]
for i,t in enumerate(tracks):
    if i in sel: continue
    ks={key2(e) for e in ends(t)}
    for net,isv,eks in EXTRA:
        if t.GetNetname()==net and isinstance(t,pcbnew.PCB_VIA)==isv and ks==eks:
            sel.add(i); print('extra added:', net, eks)
for i in sel:
    t=tracks[i]
    if isinstance(t,pcbnew.PCB_VIA):
        p=t.GetPosition(); t.SetPosition(pcbnew.VECTOR2I(p.x, p.y+mm(DY)))
    else:
        s,e=t.GetStart(),t.GetEnd()
        t.SetStart(pcbnew.VECTOR2I(s.x, s.y+mm(DY))); t.SetEnd(pcbnew.VECTOR2I(e.x, e.y+mm(DY)))
print('moved elements:', len(sel))
# post-fix 1: U2 GND stub via -> (16.3,29.6)
for t in tracks:
    if isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()=='GND':
        p=pt(t.GetPosition())
        if abs(p[0]-16.3)<0.01 and abs(p[1]-30.25)<0.01: t.SetPosition(pcbnew.VECTOR2I(mm(16.3), mm(29.6))); print('GND via relocated')
    elif not isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()=='GND':
        s,e=pt(t.GetStart()),pt(t.GetEnd())
        if abs(s[0]-16.3)<0.01 and abs(e[0]-16.3)<0.01 and abs(e[1]-30.25)<0.01:
            t.SetEnd(pcbnew.VECTOR2I(mm(16.3), mm(29.6))); print('GND seg adjusted')
# post-fix 2: 3V3 branch via near J4 (stationary): reshape to (14.85,28.85)
for t in tracks:
    if isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()=='3V3':
        p=pt(t.GetPosition())
        if abs(p[0]-14.7)<0.01 and abs(p[1]-28.7)<0.01: t.SetPosition(pcbnew.VECTOR2I(mm(14.55), mm(29.15))); print('3V3 via relocated')
    elif not isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()=='3V3' and t.GetLayer()==pcbnew.In2_Cu:
        ks={key2(e) for e in ends(t)}
        if ks=={(12.3,28.55),(14.7,28.55)}:
            s=pt(t.GetStart())
            if key2(s)==(14.7,28.55): t.SetStart(pcbnew.VECTOR2I(mm(14.55), mm(28.55)))
            else: t.SetEnd(pcbnew.VECTOR2I(mm(14.55), mm(28.55)))
            print('3V3 branch horiz adjusted')
        if ks=={(14.7,28.55),(14.7,28.7)}:
            t.SetStart(pcbnew.VECTOR2I(mm(14.55), mm(28.55))); t.SetEnd(pcbnew.VECTOR2I(mm(14.55), mm(29.15)))
            print('3V3 branch vert adjusted')
pcbnew.SaveBoard(OUT,b)
after=touch_counts(b)
diffs={k:(before[k],after[k]) for k in before if before[k]!=after.get(k)}
print('pad touch-count diffs (before,after):', diffs)
print('saved r67 placement v4')
