#!/usr/bin/env python3
"""Placement diagram (top + bottom) as PNG from the board file:
footprint courtyards/bodies as boxes, reference + value labels, pads.
For hand-assembly / reflow reference."""
import pcbnew, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")
OUT = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/placement.png")

def draw(ax, board, side):
    # board outline
    for item in board.GetDrawings():
        pass
    bb = board.GetBoardEdgesBoundingBox()
    x0, y0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
    x1, y1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="black", lw=1.5))
    want_layer = pcbnew.F_Cu if side == "top" else pcbnew.B_Cu
    for fp in board.GetFootprints():
        layers = fp.GetLayerSet()
        on_side = layers.Contains(want_layer)
        pos = fp.GetPosition()
        fx, fy = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
        fbb = fp.GetBoundingBox()
        w, h = pcbnew.ToMM(fbb.GetWidth()), pcbnew.ToMM(fbb.GetHeight())
        style = dict(fill=on_side, alpha=0.25 if on_side else 0.05,
                     ec="navy" if on_side else "gray", lw=0.8)
        ax.add_patch(Rectangle((fx - w / 2, fy - h / 2), w, h, **style))
        # pads on this side
        for pad in fp.Pads():
            pls = pad.GetLayerSet()
            if not (pls.Contains(want_layer) or pad.GetDrillSize().x > 0):
                continue
            pp = pad.GetPosition()
            ps = pad.GetSize()
            ax.add_patch(Rectangle((pcbnew.ToMM(pp.x) - pcbnew.ToMM(ps.x) / 2,
                                    pcbnew.ToMM(pp.y) - pcbnew.ToMM(ps.y) / 2),
                                   pcbnew.ToMM(ps.x), pcbnew.ToMM(ps.y),
                                   fill=True, fc="darkorange", ec="none", alpha=0.8))
            if pad.GetDrillSize().x > 0:
                ax.add_patch(Circle((pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y)),
                                    pcbnew.ToMM(pad.GetDrillSize().x) / 2,
                                    fill=True, fc="white", ec="none"))
        if on_side:
            ax.text(fx, fy, fp.GetReference(), ha="center", va="center",
                    fontsize=6, weight="bold")
            ax.text(fx, fy + h / 2 + 0.7, fp.GetValue(), ha="center", va="bottom",
                    fontsize=4.5, color="dimgray")
    ax.set_xlim(x0 - 2, x1 + 2)
    ax.set_ylim(y1 + 2, y0 - 2)  # y down (board coords)
    ax.set_aspect("equal")
    ax.set_title(f"{side} view ({'F.Cu' if side == 'top' else 'B.Cu'} side up)")
    ax.set_xlabel("mm")
    ax.set_ylabel("mm")

def main():
    b = pcbnew.LoadBoard(PATH)
    fig, axes = plt.subplots(1, 2, figsize=(11, 14))
    draw(axes[0], b, "top")
    draw(axes[1], b, "bottom")
    fig.suptitle("ZERO-WIRELESS EXT REV.A — placement (schematic positions; bottom view is as-seen from back)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT, dpi=200)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
