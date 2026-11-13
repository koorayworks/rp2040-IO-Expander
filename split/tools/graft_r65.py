import os, pcbnew
ROOT=os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
SRC=os.path.join(ROOT,'split/module_board/backup/placement_v47_round52seeds.kicad_pcb')
OUT=os.path.join(ROOT,'split/module_board/module_board.kicad_pcb')
b=pcbnew.LoadBoard(SRC)
def close(a,b2,t=0.02): return abs(a-b2)<=t
for t in list(b.GetTracks()):
    if isinstance(t,pcbnew.PCB_VIA) or t.GetNetname()!='GPIO28': continue
    s,e=t.GetStart(),t.GetEnd()
    pts=[(s.x/1e6,s.y/1e6),(e.x/1e6,e.y/1e6)]
    if (close(pts[0][0],5.55) and close(pts[0][1],21.5) and close(pts[1][0],6.2) and close(pts[1][1],21.5)) or \
       (close(pts[0][0],6.2) and close(pts[0][1],21.5) and close(pts[1][0],5.55) and close(pts[1][1],21.5)):
        b.Remove(t); print('deleted GPIO28 ext')
pcbnew.SaveBoard(OUT,b); print('saved r65')
