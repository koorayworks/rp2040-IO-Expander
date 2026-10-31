import pcbnew, sys

B = pcbnew.LoadBoard('ext_board.kicad_pcb')
F, IN2, BC = pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu
LAY = {'F': F, 'In2': IN2, 'B': BC}
def mm(x): return pcbnew.FromMM(x)
def pt(x, y): return pcbnew.VECTOR2I(mm(x), mm(y))

# ---------- footprint swap ----------
def swap_switch(ref, signal_net):
    fp = FP_CACHE[ref]
    cx, cy = pcbnew.ToMM(fp.GetPosition())
    assert abs(cx - (4.51 if ref=='SW_BOOT' else 13.51)) < 0.01 and abs(cy - 16.01) < 0.01, (ref, cx, cy)
    gi = fp.GraphicalItems()
    old_shapes = [gi[i] for i in range(gi.size())]
    for p in list(fp.Pads()):
        fp.Remove(p)
    for g in old_shapes:
        fp.Remove(g)
    net_sig = B.FindNet(signal_net); net_gnd = B.FindNet('GND')
    for num, ly, net in (('1', -2.075, net_sig), ('2', 2.075, net_gnd)):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(num)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetSize(pt(1.80, 1.35))
        pad.SetPosition(pt(0, ly))
        ls = pcbnew.LSET(); ls.AddLayer(F); ls.AddLayer(pcbnew.F_Paste); ls.AddLayer(pcbnew.F_Mask)
        pad.SetLayerSet(ls)
        pad.SetNet(net)
        fp.Add(pad)
    # silk: two side lines (body 2.90 wide x 4.00 long), fab outline + courtyard
    def line(layer, x1, y1, x2, y2, w=0.12):
        s = pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(x1, y1)); s.SetEnd(pt(x2, y2)); s.SetLayer(layer); s.SetWidth(mm(w)); fp.Add(s)
    def rect(layer, x1, y1, x2, y2, w=0.10):
        s = pcbnew.PCB_SHAPE(fp); s.SetShape(pcbnew.SHAPE_T_RECT)
        s.SetStart(pt(x1, y1)); s.SetEnd(pt(x2, y2)); s.SetLayer(layer); s.SetWidth(mm(w)); fp.Add(s)
    line(pcbnew.F_SilkS, -1.45, -2.00, -1.45, 2.00)
    line(pcbnew.F_SilkS,  1.45, -2.00,  1.45, 2.00)
    rect(pcbnew.F_Fab, -1.45, -2.00, 1.45, 2.00)
    rect(pcbnew.F_CrtYd, -1.75, -2.80, 1.75, 2.80)
    circ = pcbnew.PCB_SHAPE(fp); circ.SetShape(pcbnew.SHAPE_T_CIRCLE)
    circ.SetStart(pt(0, 0)); circ.SetEnd(pt(0.85, 0)); circ.SetLayer(pcbnew.F_Fab); circ.SetWidth(mm(0.10)); fp.Add(circ)
    fp.SetValue('TS-1088-AR02016')
    print(ref, 'swapped, center kept at', (cx, cy))

MODE = sys.argv[1] if len(sys.argv) > 1 else 'all'
FP_CACHE = {} if MODE == 'tracks' else {r: B.FindFootprintByReference(r) for r in ('SW_BOOT', 'SW_RESET')}
if MODE in ('boot', 'all'):
    swap_switch('SW_BOOT', 'BOOT')
if MODE in ('reset', 'all'):
    swap_switch('SW_RESET', 'RESET')
if MODE in ('boot', 'reset'):
    B.Save('ext_board.kicad_pcb')
    print('saved after', MODE)
    sys.exit(0)

# ---------- track surgery ----------
_TRACK_CACHE = None
def all_tracks():
    global _TRACK_CACHE
    if _TRACK_CACHE is None:
        tl = B.Tracks()
        _TRACK_CACHE = [tl[i] for i in range(tl.size())]
    return _TRACK_CACHE

def find_track(net, layer, a, b):
    hits = []
    for t in all_tracks():
        if isinstance(t, pcbnew.PCB_VIA) or t.GetNetname() != net or t.GetLayer() != layer: continue
        s, e = pcbnew.ToMM(t.GetStart()), pcbnew.ToMM(t.GetEnd())
        if (abs(s[0]-a[0])<0.011 and abs(s[1]-a[1])<0.011 and abs(e[0]-b[0])<0.011 and abs(e[1]-b[1])<0.011) or \
           (abs(s[0]-b[0])<0.011 and abs(s[1]-b[1])<0.011 and abs(e[0]-a[0])<0.011 and abs(e[1]-a[1])<0.011):
            hits.append(t)
    return hits

def find_via(net, at):
    return [t for t in all_tracks() if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname()==net
            and abs(pcbnew.ToMM(t.GetPosition())[0]-at[0])<0.011 and abs(pcbnew.ToMM(t.GetPosition())[1]-at[1])<0.011]

DEL = [
 # BOOT old links
 ('BOOT','F',(6.36,17.86),(6.36,14.16)), ('BOOT','F',(6.36,17.86),(6.36,18.66)),
 ('BOOT','F',(6.36,18.66),(6.20,18.82)),
 # TB3 old approach
 ('TB3','F',(2.80,19.38),(4.52,17.66)), ('TB3','F',(4.52,17.66),(4.52,15.00)),
 ('TB3','F',(4.52,15.00),(4.32,14.81)), ('TB3','B',(4.49,14.64),(4.32,14.81)),
 # USB_VBUS F middle
 ('USB_VBUS','F',(4.72,18.36),(4.72,16.16)), ('USB_VBUS','F',(4.94,18.58),(4.72,18.36)),
 ('USB_VBUS','F',(4.94,26.34),(4.94,18.58)),
 # USB_D- old via area
 ('USB_D-','F',(5.07,17.66),(5.20,17.79)), ('USB_D-','F',(5.20,17.79),(5.20,24.09)),
 ('USB_D-','In2',(4.29,15.92),(5.07,16.70)), ('USB_D-','In2',(5.07,16.70),(5.07,17.66)),
 # RESET old web
 ('RESET','F',(15.25,16.95),(15.36,17.06)), ('RESET','F',(15.68,18.97),(15.68,19.11)),
 ('RESET','F',(15.67,19.84),(15.39,20.12)), ('RESET','F',(15.67,19.12),(15.67,19.84)),
 ('RESET','F',(15.36,18.66),(15.37,18.66)), ('RESET','F',(15.68,19.11),(15.67,19.12)),
 ('RESET','F',(15.36,17.86),(15.36,17.06)), ('RESET','F',(15.36,14.16),(15.25,14.27)),
 ('RESET','F',(15.25,14.27),(15.25,16.95)), ('RESET','F',(15.37,18.66),(15.68,18.97)),
 ('RESET','F',(15.36,17.86),(15.36,18.66)),
 # GPIO0 north + tail stubs
 ('GPIO0','F',(14.53,17.60),(14.53,5.53)), ('GPIO0','F',(13.32,18.82),(14.53,17.60)),
 ('GPIO0','F',(13.32,20.74),(13.32,18.82)), ('GPIO0','F',(13.37,20.80),(13.32,20.74)),
 ('GPIO0','F',(13.37,20.80),(13.37,21.13)), ('GPIO0','F',(13.16,21.34),(13.37,21.13)),
 ('GPIO0','F',(13.16,23.36),(13.16,21.34)),
 # GPIO2 old via area
 ('GPIO2','F',(12.85,18.04),(12.65,18.24)), ('GPIO2','F',(12.65,18.24),(12.65,24.09)),
 ('GPIO2','In2',(12.85,9.53),(12.85,18.04)),
]
DEL_VIA = [('TB3',(4.32,14.81)), ('USB_D-',(5.07,17.66)), ('GPIO2',(12.85,18.04))]

miss = 0
for net, lay, a, b in DEL:
    hits = find_track(net, LAY[lay], a, b)
    if len(hits) != 1:
        print('DEL MISS/ MULTI', net, lay, a, b, len(hits)); miss += 1
    for h in hits: B.Remove(h)
for net, at in DEL_VIA:
    hits = find_via(net, at)
    if len(hits) != 1:
        print('VIA MISS', net, at, len(hits)); miss += 1
    for h in hits: B.Remove(h)
print('deletions done, misses:', miss)

def add_track(net, lay, a, b, w=0.10):
    t = pcbnew.PCB_TRACK(B)
    t.SetNet(B.FindNet(net)); t.SetLayer(LAY[lay]); t.SetWidth(mm(w))
    t.SetStart(pt(*a)); t.SetEnd(pt(*b)); B.Add(t)
def add_via(net, at):
    v = pcbnew.PCB_VIA(B)
    v.SetNet(B.FindNet(net)); v.SetPosition(pt(*at))
    v.SetWidth(mm(0.40)); v.SetDrill(mm(0.20)); v.SetLayerPair(F, BC); B.Add(v)

ADD = [
 # BOOT signal: top pad -> east column -> south exit (re-jog to x=6.42)
 ('BOOT','F',(4.51,13.935),(6.42,13.935),0.10), ('BOOT','F',(6.42,13.935),(6.42,18.66),0.10),
 ('BOOT','F',(6.42,18.66),(6.20,18.82),0.10),
 # BOOT GND: existing via (4.15,16.85) -> bottom pad
 ('GND','F',(4.15,16.85),(4.35,17.50),0.25),
 # TB3 new west approach
 ('TB3','F',(2.80,19.38),(3.16,18.94),0.10), ('TB3','F',(3.16,18.94),(3.16,14.70),0.10),
 ('TB3','B',(4.49,14.64),(3.16,14.70),0.10),
 # USB_VBUS: B.Cu hop over the switch zone
 ('USB_VBUS','F',(4.94,20.60),(4.94,26.34),0.10), ('USB_VBUS','B',(4.94,20.60),(4.86,20.00),0.10),
 # USB_D- new via + runs
 ('USB_D-','In2',(4.29,15.92),(6.05,17.90),0.10),
 ('USB_D-','F',(6.05,17.90),(5.98,18.50),0.10), ('USB_D-','F',(5.98,18.50),(5.98,23.60),0.10),
 ('USB_D-','F',(5.98,23.60),(5.20,24.09),0.10),
 # RESET signal: top pad -> junction; east column -> south tail
 ('RESET','F',(13.51,13.935),(15.25,14.27),0.10), ('RESET','F',(14.88,14.27),(15.25,14.27),0.10),
 ('RESET','F',(14.88,14.27),(14.88,19.62),0.10), ('RESET','F',(14.88,19.62),(15.39,20.12),0.10),
 # RESET GND link from new via
 ('GND','F',(12.62,16.98),(12.95,17.75),0.20),
 # GPIO0 west detour + B.Cu hop
 ('GPIO0','F',(14.53,5.53),(14.53,16.55),0.10), ('GPIO0','F',(14.53,16.55),(11.95,16.55),0.10),
 ('GPIO0','F',(11.95,16.55),(11.95,19.75),0.10), ('GPIO0','F',(11.95,19.75),(11.80,20.65),0.10),
 ('GPIO0','B',(11.80,20.65),(11.80,23.50),0.10), ('GPIO0','B',(11.80,23.50),(13.30,23.50),0.10),
 # GPIO2 new via + runs
 ('GPIO2','In2',(12.85,9.53),(12.85,17.30),0.10), ('GPIO2','In2',(12.85,17.30),(12.31,17.50),0.10),
 ('GPIO2','F',(12.31,17.50),(12.30,18.55),0.10), ('GPIO2','F',(12.30,18.55),(12.45,19.30),0.10),
 ('GPIO2','F',(12.45,19.30),(12.65,19.55),0.10), ('GPIO2','F',(12.65,19.55),(12.65,24.09),0.10),
]
for net, lay, a, b, w in ADD: add_track(net, lay, a, b, w)
add_via('TB3', (3.16,14.70))
add_via('USB_VBUS', (4.94,20.60))
add_via('USB_D-', (6.05,17.90))
add_via('GND', (12.62,16.98))
add_via('GPIO0', (11.80,20.65))
add_via('GPIO0', (13.30,23.50))
add_via('GPIO2', (12.31,17.50))
print('additions done')

filler = pcbnew.ZONE_FILLER(B)
filler.Fill(B.Zones())
B.Save('ext_board.kicad_pcb')
print('saved')
