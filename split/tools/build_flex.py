#!/usr/bin/env python3
"""Generate the FH35C-to-FH35C flex (FPC) board for the split module.

Design v2 (2026-11-16, supersedes the v1 two-face stagger):
Re-reading the Hirose catalog (split/ref/fh35c_catalog.pdf p.5-6)
showed the recommended FPC has ALL fingers on ONE face in two
staggered rows; the opposite face carries no copper in the mating
area and takes the stiffener (actuator side). Sources: the p.6
lamination diagrams (single-sided composition is a standard option;
the double-sided one notes the back copper must be removed at the
mating part), the p.5 plan (far-face features drawn dashed appear
only as coverlay/stiffener edges), and the p.1 insertion photo
(fingers visible on one face only).

- Both ends identical: fingers on F.Cu, stiffener on B.Cu side.
  Order as a 1-layer FPC (B.Cu carries no copper at all).
- Finger rows (catalog p.5): pitch 0.3, finger width 0.2.
  Deep row = odd contacts, centers 0.3..9.3 (span C=9.0), tips at
  the FPC edge. Shallow row = even contacts, centers 0.6..9.0
  (span B=8.4), tips set back 0.85 from the edge.
- Finger copper (0.2 wide) runs to 2.25 from the tip on both rows;
  the coverlay window ends at 2.1, so exposed lengths are
  deep 2.1 / shallow 1.25 (matches the 2.1 and (1.25) catalog dims).
  Traces (0.15 wide) continue from 2.25, straight 1:1, no vias.
- Misalignment check mark (catalog reference geometry 0.5 x 1.25):
  approximated as a copper bump on contact 1 at each end,
  t = 1.25..1.75 from the tip, reaching toward the left edge.
- Stiffener zones 2.85 from each tip, drawn on User.1 (both ends);
  exported as the JLC PI stiffener layer (back side, pib_).
  Mating thickness 0.2 +/- 0.03 is an order-time spec.
- Channel order = split/FFC_PINMAP_30P.md (contact m = channel m).
  Contact 31 is NC but gets a full through trace on net NC31 like
  every other lane: the assembled mating parity lands this lane on
  the ch1 (VSYS) path, so a finger-only dummy would leave VSYS open.
- If the first-article continuity check shows the channel order
  reversed, the fix is a mirrored flex (fingers on B.Cu); the two
  rigid boards stay untouched.

Coordinates: x across the flex (0..9.6), y along length, end A tip
at y=0, end B tip at y=L. Usage: build_flex.py [length_mm] [outdir]
"""
import os, sys
import pcbnew

L = float(sys.argv[1]) if len(sys.argv) > 1 else 100.0
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser(
    '~/workspace/projects/rp2040-IO-Expander/split/flex')

W = 9.6            # FPC width (catalog F for 31S)
FING_W = 0.20      # finger width
TRACE_W = 0.15
SETBACK = 0.85     # shallow-row tip setback from the edge
CU_END = 2.25      # finger copper (0.2 wide) ends this far from tip
WIN_END = 2.1      # coverlay window ends this far from tip
STIFF = 2.85       # stiffener length from tip

# channel -> net name (FFC_PINMAP_30P.md). Contact 31 is NC on the
# rigid boards, but its lane still needs a through trace on a named
# net (NC31): in the assembled state the connector mating parity
# puts this lane on the ch1 (VSYS) path, and an unnamed finger-only
# lane is invisible to DRC and net-based audits (this was a real
# defect until 2026-11-16: VSYS open end to end).
CHAN = {1:'VSYS',2:'GND',3:'3V3',4:'GPIO29',5:'GPIO28',6:'GPIO27',
        7:'GPIO26',8:'GPIO15',9:'GPIO14',10:'GPIO13',11:'GPIO12',
        12:'GPIO11',13:'GPIO10',14:'GPIO9',15:'GPIO8',16:'GPIO7',
        17:'GPIO6',18:'GPIO5',19:'GPIO4',20:'GPIO3',21:'GPIO2',
        22:'GPIO1',23:'GPIO0',24:'GND',25:'USB_D-',26:'USB_D+',
        27:'GND',28:'BOOT',29:'RESET',30:'STATUS_LED',31:'NC31'}

def mm(v): return pcbnew.FromMM(v)

b = pcbnew.BOARD()
b.SetCopperLayerCount(2)

# Embed the FPC design rules in the board (same values as the
# project file) so a standalone DRC of the .kicad_pcb uses them:
# the finger-field gap is 0.10 by Hirose's own design (0.2 fingers
# at 0.3 pitch), and fingers intentionally touch the tip edge.
_ds = b.GetDesignSettings()
_ds.m_MinClearance = mm(0.1)
_ds.m_CopperEdgeClearance = mm(0.1)
_ds.m_TrackMinWidth = mm(0.1)
b.GetAllNetClasses()['Default'].SetClearance(mm(0.1))

nets = {}
def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
        nets[name] = n
    return nets[name]

def cx(m):
    """Contact center x: odd (deep) row centers 0.3..9.3 (span
    C=9.0), even (shallow) row centers 0.6..9.0 (span B=8.4)."""
    if m % 2 == 1:
        return 0.3 + (m - 1) * 0.3          # 0.3, 0.9, ..., 9.3
    return 0.6 + (m - 2) * 0.3              # 0.6, 1.2, ..., 9.0

def track(board, layer, x0, y0, x1, y1, width, n=None):
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
    t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetWidth(mm(width))
    t.SetLayer(layer)
    if n is not None:
        t.SetNet(n)
    board.Add(t)
    return t

def rect_shape(board, layer, x0, y0, x1, y1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
    s.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    s.SetLayer(layer)
    s.SetFilled(True)
    board.Add(s)
    return s

F = pcbnew.F_Cu

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
    tip = 0.0 if m % 2 == 1 else SETBACK   # deep row tips at the edge
    n = net(CHAN[m]) if m in CHAN else None
    # end A: finger (0.2 wide) from its tip to CU_END, at y = tip..CU_END
    track(b, F, x, tip, x, CU_END, FING_W, n)
    # end B: mirrored (tip at y=L)
    track(b, F, x, L - tip, x, L - CU_END, FING_W, n)
    # through trace (0.15 wide) joining the two finger ends
    if m in CHAN:
        track(b, F, x, CU_END, x, L - CU_END, TRACE_W, n)

# coverlay windows (F.Mask openings), one per end, full width,
# open at the tip edge, ending at WIN_END from the tip
rect_shape(b, pcbnew.F_Mask, -0.05, -0.05, W + 0.05, WIN_END)
rect_shape(b, pcbnew.F_Mask, -0.05, L - WIN_END, W + 0.05, L + 0.05)

# misalignment check marks (reference geometry, approximated):
# bump on contact 1 (VSYS), t = 1.25..1.75 from each tip
vsys = net('VSYS')
track(b, F, 0.20, 1.43, 0.20, 1.57, 0.36, vsys)
track(b, F, 0.20, L - 1.57, 0.20, L - 1.43, 0.36, vsys)

# stiffener zones (back side), 2.85 from each tip, on User.1
rect_shape(b, pcbnew.User_1, 0, 0, W, STIFF)
rect_shape(b, pcbnew.User_1, 0, L - STIFF, W, L)

os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, f'flex_{int(L)}mm.kicad_pcb')
b.Save(path)
print('saved', path)
