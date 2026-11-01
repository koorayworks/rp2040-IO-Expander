import pcbnew, math

BASE = "/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/"
src = open(BASE + "route3.py").read()
head = src.split("# ---------------- grid A*")[0]
head = head.replace('SRC = "backups/board_micro9.kicad_pcb"',
                    'SRC = "%sbackups/board_route5.kicad_pcb"' % BASE)
g = {}
exec(head, g)
b = g["b"]; items = g["items"]; pads = g["pads"]; validate = g["validate"]
TM = pcbnew.ToMM; FM = pcbnew.FromMM
LAYV = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LAYN = {pcbnew.F_Cu: 0, pcbnew.In2_Cu: 1, pcbnew.B_Cu: 2}

def r3(v): return round(v, 3)

def delete_tracks(net, layer_idx, match):
    victims = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA": continue
        if t.GetNetname() != net: continue
        if LAYN.get(t.GetLayer()) != layer_idx: continue
        a, c = t.GetStart(), t.GetEnd()
        x1, y1, x2, y2 = r3(TM(a.x)), r3(TM(a.y)), r3(TM(c.x)), r3(TM(c.y))
        if match(x1, y1, x2, y2) or match(x2, y2, x1, y1):
            victims.append(t)
    for t in victims: b.Remove(t)
    keep = []
    for it in items:
        if it["k"] == "T" and it["net"] == net and it["l"] == layer_idx:
            if match(r3(it["x1"]), r3(it["y1"]), r3(it["x2"]), r3(it["y2"])) or \
               match(r3(it["x2"]), r3(it["y2"]), r3(it["x1"]), r3(it["y1"])):
                continue
        keep.append(it)
    items[:] = keep
    return len(victims)

def add_cands(net, cands):
    netobj = b.FindNet(net)
    assert netobj is not None, net
    for cd in cands:
        if cd[0] == "T":
            _, l, x1, y1, x2, y2 = cd
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(FM(x1), FM(y1)))
            t.SetEnd(pcbnew.VECTOR2I(FM(x2), FM(y2)))
            t.SetWidth(FM(0.10)); t.SetLayer(LAYV[l]); t.SetNet(netobj)
            b.Add(t)
            items.append({"k": "T", "net": net, "l": l, "x1": x1, "y1": y1, "x2": x2, "y2": y2})
        else:
            _, x, y = cd
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(FM(x), FM(y)))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetDrill(FM(0.20)); v.SetWidth(FM(0.40)); v.SetNet(netobj)
            b.Add(v)
            items.append({"k": "V", "net": net, "x": x, "y": y})

def job(name, net, cands):
    bad = validate(cands, net)
    if bad:
        print(f"== {name}: {len(bad)} violations, NOT applied")
        for i, desc, d, req in bad:
            print(f"   cand{i} {cands[i]} vs {desc}: {d:.3f} < {req:.2f}")
        return False
    add_cands(net, cands)
    print(f"== {name}: CLEAN, applied {len(cands)} items")
    return True

# ---- S0': MODE_STAIR north shift ----
n1 = delete_tracks("3V3_USB", 2, lambda x1, y1, x2, y2: (x1, y1) == (3.00, 29.56) and (x2, y2) == (3.25, 29.00))
n2 = delete_tracks("3V3_USB", 2, lambda x1, y1, x2, y2: (x1, y1) == (3.25, 29.00) and (x2, y2) == (4.80, 29.05))
n3 = delete_tracks("3V3_USB", 2, lambda x1, y1, x2, y2: (x1, y1) == (4.80, 29.05) and (x2, y2) == (4.80, 30.60))
print("S0' deletions:", n1, n2, n3)
s0 = [("T", 2, 3.00, 29.56, 3.20, 28.35),
      ("T", 2, 3.20, 28.35, 4.45, 28.58),
      ("T", 2, 4.45, 28.58, 4.80, 29.10)]
if n3:
    s0.append(("T", 2, 4.80, 29.10, 4.80, 30.60))
job("S0'", "3V3_USB", s0)

# ---- VIN2 v5: B north -> via (5.85,31.20) -> F east -> BAT via (8.70,31.50) ----
job("VIN2", "3V3_BAT", [
    ("T", 2, 3.50, 29.56, 3.55, 28.80),
    ("T", 2, 3.55, 28.80, 5.72, 28.80),
    ("T", 2, 5.72, 28.80, 5.72, 31.20),
    ("T", 2, 5.72, 31.20, 5.85, 31.20),
    ("V", 5.85, 31.20),
    ("T", 0, 5.85, 31.20, 7.20, 31.20),
    ("T", 0, 7.20, 31.20, 7.20, 34.35),
    ("T", 0, 7.20, 34.35, 8.55, 34.35),
    ("T", 0, 8.55, 34.35, 8.55, 31.50),
    ("T", 0, 8.55, 31.50, 8.70, 31.50)])

# ---- VIN1 v3: U4.3 -> STAIR bit (5.00,31.55) ----
job("VIN1", "3V3_USB", [
    ("T", 2, 3.50, 31.04, 3.85, 30.98),
    ("T", 2, 3.85, 30.98, 4.45, 31.05),
    ("T", 2, 4.45, 31.05, 4.45, 31.60),
    ("T", 2, 4.45, 31.60, 5.00, 31.55)])

# ---- PR1a v5: U4.4 -> PR1b B row at (4.15,35.95) ----
job("PR1a", "PR1", [
    ("T", 2, 3.00, 31.04, 2.80, 31.82),
    ("T", 2, 2.80, 31.82, 3.30, 32.80),
    ("T", 2, 3.30, 32.80, 4.20, 33.35),
    ("T", 2, 4.20, 33.35, 4.15, 33.60),
    ("T", 2, 4.15, 33.60, 4.15, 35.95)])

# ---- LEG v7: U2.5 -> west -> south -> STAIR B row west end (2.95,34.15) ----
job("LEG", "3V3_USB", [
    ("T", 2, 6.64, 20.50, 2.20, 20.50),
    ("T", 2, 2.20, 20.50, 2.20, 34.15),
    ("T", 2, 2.20, 34.15, 2.95, 34.15)])

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
b.Save(BASE + "backups/board_route7.kicad_pcb")
print("saved backups/board_route7.kicad_pcb")
