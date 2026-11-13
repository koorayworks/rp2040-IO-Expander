# Production data export for the split boards (Zero / Module).
# Usage: python3 export_production.py <board_dir> <board_name>
# Writes: <board_dir>/gerber/* (Protel ext, same style as ext_board), drill,
#         <board_dir>/<board_name>_bom_jlc.csv, <board_dir>/<board_name>_cpl_jlc.csv
import pcbnew, os, sys, csv

BASE = os.path.abspath(sys.argv[1]); NAME = sys.argv[2]
b = pcbnew.LoadBoard(os.path.join(BASE, NAME + '.kicad_pcb'))
outdir = os.path.join(BASE, 'gerber'); os.makedirs(outdir, exist_ok=True)
pc = pcbnew.PLOT_CONTROLLER(b); opts = pc.GetPlotOptions()
opts.SetOutputDirectory(outdir); opts.SetPlotFrameRef(False)
opts.SetUseGerberProtelExtensions(True)
LAYERS = [(pcbnew.F_Cu,'F_Cu'),(pcbnew.In1_Cu,'In1_Cu'),(pcbnew.In2_Cu,'In2_Cu'),
          (pcbnew.B_Cu,'B_Cu'),(pcbnew.F_Mask,'F_Mask'),(pcbnew.B_Mask,'B_Mask'),
          (pcbnew.F_Paste,'F_Paste'),(pcbnew.B_Paste,'B_Paste'),
          (pcbnew.F_SilkS,'F_Silkscreen'),(pcbnew.B_SilkS,'B_Silkscreen'),
          (pcbnew.Edge_Cuts,'Edge_Cuts')]
for layer, suffix in LAYERS:
    pc.SetLayer(layer); pc.OpenPlotfile(suffix, pcbnew.PLOT_FORMAT_GERBER, '')
    pc.PlotLayer(); pc.ClosePlot()
pc.ClosePlot()
# drill (Excellon, merged PTH+NPTH)
dw = pcbnew.EXCELLON_WRITER(b)
dw.SetOptions(True, False, pcbnew.VECTOR2I(0,0), False)
dw.CreateDrillandMapFilesSet(outdir, True, False)
print('GERBER+DRILL DONE ->', outdir)
