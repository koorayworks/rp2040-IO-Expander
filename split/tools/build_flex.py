#!/usr/bin/env python3
"""Generate the FH35C-to-FH35C flex (FPC) board for the split module.

Design (frozen 2026-11-11):
- Both ends FH35C-31S-0.3SHW fingers per Hirose catalog recommended FPC
  (split/ref/fh35c_catalog.pdf p.5): width F=9.6, contact spans C=9.0
  (odd contacts, 16) / B=8.4 (even contacts, 15), pitch 0.3, finger
  width 0.2, total mating thickness 0.2 (stiffener, order-time spec).
- Channel order = split/FFC_PINMAP_30P.md (contact m = channel m,
  contact 31 = dummy, no trace).
- Odd channels run on B.Cu, even channels on F.Cu (stagger faces).
  Traces are straight 1:1, no vias. END_B_FLIP swaps the face
  assignment at the far end for flipped connector mounting
  (decided at first-article check; default False).
- Exposed finger lengths: odd (B.Cu) 2.25, even (F.Cu) 1.75
  (catalog two-depth stagger; face/length pairing to be confirmed
  against the drawing at first article).
- Stiffener zones drawn on User layers (2.85 from each tip);
  mask openings over the finger fields act as coverlay windows.

Coordinates: x across the flex (0..9.6), y along length, end A tip at
y=0, end B tip at y=L. Usage: build_flex.py [length_mm] [outdir]
"""
import os, sys
import pcbnew

L = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser(
    '~/workspace/projects/rp2040-IO-Expander/split/flex')
END_B_FLIP = False

W = 9.6            # FPC width (catalog F for 31S)
PITCH = 0.3
FING_W = 0.20      # finger width
TRACE_W = 0.15
EXP_ODD = 2.25     # exposed length, odd contacts (B.Cu)
EXP_EVEN = 1.75    # exposed length, even contacts (F.Cu)
STIFF = 2.85       # stiffener length from tip
EDGE_MARGIN = 0.30 # F edge to C-row outer finger edge zone

# channel -> net name (FFC_PINMAP_30P.md); contact 31 unused
CHAN = {1:'VSYS',2:'GND',3:'3V3',4:'GPIO29',5:'GPIO28',6:'GPIO27',
        7:'GPIO26',8:'GPIO15',9:'GPIO14',10:'GPIO13',11:'GPIO12',
        12:'GPIO11',13:'GPIO10',14:'GPIO9',15:'GPIO8',16:'GPIO7',
        17:'GPIO6',18:'GPIO5',19:'GPIO4',20:'GPIO3',21:'GPIO2',
        22:'GPIO1',23:'GPIO0',24:'GND',25:'USB_D-',26:'USB_D+',
        27:'GND',28:'BOOT',29:'RESET',30:'STATUS_LED'}

def mm(v): return pcbnew.FromMM(v)

b = pcbnew.BOARD()
b.SetCopperLayerCount(2)

nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
        nets[name] = n
    return nets[name]

def cx(m):
    """Contact center x: odd row centers 0.3..9.3 (span C=9.0),
    even row centers 0.6..9.0 (span B=8.4), staggered by 0.3."""
    if m % 2 == 1:
        return 0.3 + (m - 1) * 0.3          # 0.3, 0.9, ..., 9.3
    return 0.6 + (m - 2) * 0.3              # 0.6, 1.2, ..., 9.0

def rect(board, layer, x0, y0, x1, y1, width=0.0, net=None, kind='track'):
    if kind == 'track':
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        t.SetWidth(mm(width))
        t.SetLayer(layer)
        if net is not None:
            t.SetNet(net)
        board.Add(t)
        return t
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetLayer(layer)
    s.SetFilled(True)
    board.Add(s)
    return s

F = pcbnew.F_Cu; Bk = pcbnew.B_Cu

# outline
for (x0, y0, x1, y1) in [(0, 0, W, 0), (W, 0, W, L), (W, L, 0, L), (0, L, 0, 0)]:
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.05))
    b.Add(s)

for m in range(1, 32):
    x = cx(m)
    odd = (m % 2 == 1)
    layerA = Bk if odd else F
    expA = EXP_ODD if odd else EXP_EVEN
    layerB = layerA if not END_B_FLIP else (F if layerA == Bk else Bk)
    expB = expA if not END_B_FLIP else (EXP_EVEN if odd else EXP_ODD)
    n = net(CHAN[m]) if m in CHAN else None
    # finger at end A (tip y=0, exposed from 0 to expA, copper continues
    # as trace under coverlay): a track of width FING_W centered on x
    rect(b, layerA, x, 0, x, expA + 1.0, FING_W, n)
    # finger at end B (tip y=L)
    rect(b, layerB, x, L, x, L - expB - 1.0, FING_W, n)
    # through trace (same layer end to end when not flipped)
    if m in CHAN:
        if layerA == layerB:
            rect(b, layerA, x, expA, x, L - expB, TRACE_W, n)
        else:
            # flipped far end: drop a via mid-flex (not expected v1)
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(L/2)))
            v.SetWidth(mm(0.45)); v.SetDrill(mm(0.25))
            v.SetLayerPair(F, Bk)
            v.SetNet(n)
            b.Add(v)
            rect(b, layerA, x, expA, x, L/2, TRACE_W, n)
            rect(b, layerB, x, L/2, x, L - expB, TRACE_W, n)
    # mask openings (coverlay windows) over exposed fingers
    ml = pcbnew.F_Mask if layerA == F else pcbnew.B_Mask
    rect(b, ml, x - FING_W/2 - 0.03, -0.01, x + FING_W/2 + 0.03, expA + 0.05, kind='shape')
    ml2 = pcbnew.F_Mask if layerB == F else pcbnew.B_Mask
    rect(b, ml2, x - FING_W/2 - 0.03, L - expB - 0.05, x + FING_W/2 + 0.03, L + 0.01, kind='shape')
    # stiffener annotation (User.1 = end A back side, User.2 = end B)
    rect(b, pcbnew.User_1, 0, 0, W, STIFF, kind='shape')
    rect(b, pcbnew.User_2, 0, L - STIFF, W, L, kind='shape')

os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, f'flex_{int(L)}mm.kicad_pcb')
b.Save(path)
print('saved', path)
