import os, pcbnew
ROOT=os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC=os.path.join(ROOT,'split/module_board/backup/placement_v47_round52seeds.kicad_pcb')
OUT=os.path.join(ROOT,'split/module_board/module_board.kicad_pcb')
b=pcbnew.LoadBoard(SRC)
def close(a,b2,t=0.02): return abs(a-b2)<=t
def del_seg(net,layer,x1,y1,x2,y2):
    for t in list(b.GetTracks()):
        if isinstance(t,pcbnew.PCB_VIA) or t.GetNetname()!=net or t.GetLayer()!=layer: continue
        s,e=t.GetStart(),t.GetEnd()
        pts=[(s.x/1e6,s.y/1e6),(e.x/1e6,e.y/1e6)]
        if (close(pts[0][0],x1) and close(pts[0][1],y1) and close(pts[1][0],x2) and close(pts[1][1],y2)) or \
           (close(pts[0][0],x2) and close(pts[0][1],y2) and close(pts[1][0],x1) and close(pts[1][1],y1)):
            b.Remove(t); return True
    return False
def del_via(net,x,y):
    for t in list(b.GetTracks()):
        if not isinstance(t,pcbnew.PCB_VIA) or t.GetNetname()!=net: continue
        p=t.GetPosition()
        if close(p.x/1e6,x) and close(p.y/1e6,y): b.Remove(t); return True
    return False
F=pcbnew.F_Cu
print('del1', del_seg('GPIO7',F,9.8,17.363,9.787,15.285))
print('del2', del_seg('GPIO7',F,9.787,15.285,10.659,14.413))
print('del3', del_seg('GPIO7',F,10.659,14.413,10.659,14.207))
print('delv', del_via('GPIO7',10.659,14.207))
pcbnew.SaveBoard(OUT,b); print('saved r64')
