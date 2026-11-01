import pcbnew, os
BASE = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board_revb")
b = pcbnew.LoadBoard(os.path.join(BASE, "ext_board_revb.kicad_pcb"))
outdir = os.path.join(BASE, "gerber")
os.makedirs(outdir, exist_ok=True)
pc = pcbnew.PLOT_CONTROLLER(b)
opts = pc.GetPlotOptions()
opts.SetOutputDirectory(outdir)
opts.SetPlotFrameRef(False)
try:
    opts.SetUseGerberProtelExtensions(True)
except Exception as e:
    print("protel ext:", e)
LAYERS = [
    (pcbnew.F_Cu, "F_Cu"), (pcbnew.In1_Cu, "In1_Cu"), (pcbnew.In2_Cu, "In2_Cu"),
    (pcbnew.B_Cu, "B_Cu"), (pcbnew.F_Mask, "F_Mask"), (pcbnew.B_Mask, "B_Mask"),
    (pcbnew.F_Paste, "F_Paste"), (pcbnew.B_Paste, "B_Paste"),
    (pcbnew.F_SilkS, "F_Silkscreen"), (pcbnew.B_SilkS, "B_Silkscreen"),
    (pcbnew.Edge_Cuts, "Edge_Cuts"),
]
for layer, suffix in LAYERS:
    pc.SetLayer(layer)
    pc.OpenPlotfile(suffix, pcbnew.PLOT_FORMAT_GERBER, "")
    pc.PlotLayer()
    pc.ClosePlot()
    print("plotted", suffix)
print("PLOT DONE")
