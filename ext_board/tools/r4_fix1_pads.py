#!/usr/bin/env python3
"""Round 4 fix 1: repair switch pad positions (SetPosition takes BOARD coords),
then rotate SW_RESET 180 deg so pad1(RESET) is the bottom pad, pad2(GND) top,
matching the SW_BOOT convention (pad1=signal top for BOOT; for RESET the
footprint is flipped so the signal pad faces its southbound route)."""
import pcbnew

IU = pcbnew.FromMM(1)
P = 'ext_board.kicad_pcb'
bd = pcbnew.LoadBoard(P)

def mm(x, y):
    return pcbnew.VECTOR2I(int(round(x * IU)), int(round(y * IU)))

for ref, cx in (('SW_BOOT', 4.51), ('SW_RESET', 13.51)):
    fp = bd.FindFootprintByReference(ref)
    assert fp is not None, ref
    pos = fp.GetPosition()
    print(ref, 'fp at (%.3f, %.3f)' % (pos.x / IU, pos.y / IU))
    for pad in fp.Pads():
        num = pad.GetNumber()
        ty = 13.935 if num == '1' else 18.085
        pad.SetPosition(mm(cx, ty))
    # verify
    for pad in fp.Pads():
        pp = pad.GetPosition()
        print('  pad', pad.GetNumber(), pad.GetNetname(),
              'board (%.3f, %.3f)' % (pp.x / IU, pp.y / IU))

# rotate SW_RESET 180 degrees about its center
fp = bd.FindFootprintByReference('SW_RESET')
fp.SetOrientation(pcbnew.EDA_ANGLE(180, pcbnew.DEGREES_T))
for pad in fp.Pads():
    pp = pad.GetPosition()
    print('SW_RESET after rotate: pad', pad.GetNumber(), pad.GetNetname(),
          'board (%.3f, %.3f)' % (pp.x / IU, pp.y / IU))

bd.Save(P)
print('saved')
