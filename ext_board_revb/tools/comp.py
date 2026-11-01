import pcbnew, math
TM = pcbnew.ToMM
b = pcbnew.LoadBoard("/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/backups/board_route5.kicad_pcb")
LAYN = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}
def pt_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy
    if L2 == 0: return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
def seg_seg(a, c, d, e):
    def o(p, q, r): return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    d1, d2, d3, d4 = o(d, e, a), o(d, e, c), o(a, c, d), o(a, c, e)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)): return 0.0
    return min(pt_seg(a[0], a[1], d[0], d[1], e[0], e[1]), pt_seg(c[0], c[1], d[0], d[1], e[0], e[1]),
               pt_seg(d[0], d[1], a[0], a[1], c[0], c[1]), pt_seg(e[0], e[1], a[0], a[1], c[0], c[1]))

for NET in ("3V3_BAT", "3V3_USB", "PR1", "VBAT"):
    items = []
    for t in b.GetTracks():
        if t.GetNetname() != NET: continue
        a, c = t.GetStart(), t.GetEnd()
        if t.GetClass() == "PCB_VIA":
            items.append(("V", TM(a.x), TM(a.y)))
        elif t.GetLayer() in LAYN:
            items.append(("T", LAYN[t.GetLayer()], TM(a.x), TM(a.y), TM(c.x), TM(c.y)))
    pads = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() != NET: continue
            cen = pad.GetPosition()
            pads.append((f"{fp.GetReference()}.{pad.GetNumber()}", TM(cen.x), TM(cen.y),
                         {LAYN[l] for l in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu) if pad.IsOnLayer(l)}))
    n = len(items)
    par = list(range(n + len(pads)))
    def find(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    def uni(x, y):
        x, y = find(x), find(y)
        if x != y: par[x] = y
    def touch(i, j):
        A, B = items[i], items[j]
        if A[0] == "V" and B[0] == "V": return math.hypot(A[1] - B[1], A[2] - B[2]) <= 0.401
        if A[0] == "V" and B[0] == "T": return pt_seg(A[1], A[2], B[2], B[3], B[4], B[5]) <= 0.251
        if A[0] == "T" and B[0] == "V": return pt_seg(B[1], B[2], A[2], A[3], A[4], A[5]) <= 0.251
        if A[1] != B[1]: return False
        return seg_seg((A[2], A[3]), (A[4], A[5]), (B[2], B[3]), (B[4], B[5])) <= 0.101
    for i in range(n):
        for j in range(i + 1, n):
            if touch(i, j): uni(i, j)
    for pi, (nm, px, py, lays) in enumerate(pads):
        for i, it in enumerate(items):
            if it[0] == "V":
                if math.hypot(px - it[1], py - it[2]) <= 0.21: uni(n + pi, i)
            elif it[1] in lays and pt_seg(px, py, it[2], it[3], it[4], it[5]) <= 0.06:
                uni(n + pi, i)
    comps = {}
    for pi, (nm, px, py, lays) in enumerate(pads):
        comps.setdefault(find(n + pi), []).append(nm)
    orphan = [i for i in range(n) if all(find(i) != find(n + pi) for pi in range(len(pads)))]
    print(f"{NET}: {len(comps)} pad-components")
    for k, v in comps.items(): print("   ", v)
    if orphan: print("    orphan items (no pad):", len(orphan))
