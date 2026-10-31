#!/usr/bin/env python3
"""Round 4 fix 12: repair switch footprint graphics.
r4_swap passed LOCAL coordinates to PCB_SHAPE.SetStart/SetEnd, which
expect BOARD coordinates (stored = passed - fp position, un-rotated),
so all silk/fab/courtyard shapes of SW_BOOT / SW_RESET landed one
footprint-position away from their pads. Re-set them with proper
board-frame coordinates so the stored locals match the intent:
  F.SilkS lines x=+/-1.45, y -2.00..2.00 (body 2.90 x 4.00)
  F.Fab   rect  (-1.45,-2.00)-(1.45,2.00), circle centre (0,0) r 0.85
  F.CrtYd rect  (-1.75,-2.80)-(1.75,2.80)
"""
import pcbnew, math

IU = pcbnew.FromMM(1)
P = 'ext_board.kicad_pcb'
bd = pcbnew.LoadBoard(P)

INTENDED = [
    # (layer, shape type, local p1, local p2)
    (pcbnew.F_SilkS, pcbnew.SHAPE_T_SEGMENT, (-1.45, -2.00), (-1.45, 2.00)),
    (pcbnew.F_SilkS, pcbnew.SHAPE_T_SEGMENT, (1.45, -2.00), (1.45, 2.00)),
    (pcbnew.F_Fab, pcbnew.SHAPE_T_RECT, (-1.45, -2.00), (1.45, 2.00)),
    (pcbnew.F_CrtYd, pcbnew.SHAPE_T_RECT, (-1.75, -2.80), (1.75, 2.80)),
    (pcbnew.F_Fab, pcbnew.SHAPE_T_CIRCLE, (0.0, 0.0), (0.85, 0.0)),
]

def v2(x, y):
    return pcbnew.VECTOR2I(int(round(x * IU)), int(round(y * IU)))

for ref in ('SW_BOOT', 'SW_RESET'):
    fp = bd.FindFootprintByReference(ref)
    pos = fp.GetPosition()
    bx, by = pos.x / IU, pos.y / IU
    th = math.radians(fp.GetOrientationDegrees())
    c, s = round(math.cos(th)), round(math.sin(th))

    def to_board(lx, ly):
        return (bx + lx * c - ly * s, by + lx * s + ly * c)

    used = set()
    fixed = 0
    for g in fp.GraphicalItems():
        for i, (lay, typ, p1, p2) in enumerate(INTENDED):
            if i in used:
                continue
            if g.GetLayer() == lay and g.GetShape() == typ:
                g.SetStart(v2(*to_board(*p1)))
                g.SetEnd(v2(*to_board(*p2)))
                used.add(i)
                fixed += 1
                break
        else:
            print('  note: unmatched shape in', ref, g.GetClass(), g.GetLayer(), g.GetShape())
    print(ref, 'fixed', fixed, 'of', len(INTENDED), 'shapes at pos (%.2f,%.2f) rot %s' % (bx, by, fp.GetOrientationDegrees()))

filler = pcbnew.ZONE_FILLER(bd)
filler.Fill(bd.Zones())
bd.Save(P)
print('saved')
