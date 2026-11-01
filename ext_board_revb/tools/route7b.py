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

# ---- VIN2: U4.6 -> BAT via (8.70,31.50) ----
job("VIN2", "3V3_BAT", [
    ("T", 2, 3.50, 29.56, 4.40, 31.30),
    ("T", 2, 4.40, 31.30, 5.90, 30.30),
    ("T", 2, 5.90, 30.30, 5.90, 28.80),
    ("T", 2, 5.90, 28.80, 8.56, 28.80),
    ("T", 2, 8.56, 28.80, 8.56, 31.50),
    ("T", 2, 8.56, 31.50, 8.70, 31.50)])

# ---- VIN1: U4.3 -> STAIR staircase bit (4.45,33.55) ----
job("VIN1", "3V3_USB", [
    ("T", 2, 3.50, 31.04, 3.55, 32.55),
    ("T", 2, 3.55, 32.55, 3.90, 32.15),
    ("T", 2, 3.90, 32.15, 4.45, 32.15),
    ("T", 2, 4.45, 32.15, 4.45, 33.55)])

# ---- PR1a: U4.4 -> PR1 I2 chain bit (2.70,35.60) ----
job("PR1a", "PR1", [
    ("T", 2, 3.00, 31.04, 3.05, 32.50),
    ("T", 2, 3.05, 32.50, 3.22, 32.68),
    ("T", 2, 3.22, 32.68, 3.40, 33.90),
    ("T", 2, 3.40, 33.90, 2.20, 33.90),
    ("T", 2, 2.20, 33.90, 2.20, 35.60),
    ("T", 2, 2.20, 35.60, 2.55, 35.60),
    ("V", 2.55, 35.60),
    ("T", 1, 2.55, 35.60, 2.70, 35.60)])

# ---- LEG: U2.5 -> STAIR staircase bit (4.70,33.30) ----
job("LEG", "3V3_USB", [
    ("T", 2, 6.64, 20.50, 6.55, 19.70),
    ("V", 6.55, 19.70),
    ("T", 1, 6.55, 19.70, 6.05, 20.45),
    ("T", 1, 6.05, 20.45, 5.70, 20.80),
    ("T", 1, 5.70, 20.80, 5.65, 24.40),
    ("T", 1, 5.65, 24.40, 6.40, 24.40),
    ("V", 6.40, 24.40),
    ("T", 2, 6.40, 24.40, 6.40, 32.70),
    ("T", 2, 6.40, 32.70, 6.00, 34.60),
    ("T", 2, 6.00, 34.60, 5.45, 34.10),
    ("T", 2, 5.45, 34.10, 4.70, 33.30)])

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.GetZoneList())
b.Save(BASE + "backups/board_route7.kicad_pcb")
print("saved backups/board_route7.kicad_pcb")
