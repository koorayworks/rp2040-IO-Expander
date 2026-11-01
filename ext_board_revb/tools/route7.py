import pcbnew, math

BASE = "/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/"
# --- load route3 head (geometry + items/pads + validate) with SRC=board_route5 ---
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
    """match(x1,y1,x2,y2)->bool on rounded mm coords. Collect then remove (pcbnew quirk)."""
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
    # mirror in items
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

# ---------------- S0': move MODE_STAIR seg_a/seg_b/seg_c north ----------------
n1 = delete_tracks("3V3_USB", 2, lambda x1, y1, x2, y2: (x1, y1) == (3.00, 29.56) and (x2, y2) == (3.25, 29.00))
n2 = delete_tracks("3V3_USB", 2, lambda x1, y1, x2, y2: (x1, y1) == (3.25, 29.00) and (x2, y2) == (4.80, 29.05))
n3 = delete_tracks("3V3_USB", 2, lambda x1, y1, x2, y2: (x1, y1) == (4.80, 29.05) and (x2, y2) == (4.80, 30.60))
print("S0' deletions: seg_a", n1, "seg_b", n2, "vertical", n3)
s0 = [("T", 2, 3.00, 29.56, 3.20, 28.35),
      ("T", 2, 3.20, 28.35, 4.45, 28.58),
      ("T", 2, 4.45, 28.58, 4.80, 29.30)]
if n3:  # restore vertical continuity south of the new landing point
    s0.append(("T", 2, 4.80, 29.30, 4.80, 30.60))
job("S0'", "3V3_USB", s0)

# ---------------- VIN2: U4.6 -> 3V3_BAT ----------------
vin2 = [("T", 2, 3.50, 29.56, 4.05, 30.60),
        ("T", 2, 4.05, 30.60, 4.05, 31.82),
        ("T", 2, 4.05, 31.82, 5.16, 31.86),
        ("T", 2, 5.16, 31.86, 5.24, 31.38),
        ("T", 2, 5.24, 31.38, 5.24, 29.10),
        ("T", 2, 5.24, 29.10, 5.30, 29.02),
        ("V", 5.30, 29.02),
        ("T", 0, 5.30, 29.02, 4.80, 29.30),
        ("T", 0, 4.80, 29.30, 4.80, 35.45),
        ("T", 0, 4.80, 35.45, 6.55, 35.45),
        ("T", 0, 6.55, 35.45, 6.90, 36.05),
        ("V", 6.90, 36.05)]
job("VIN2", "3V3_BAT", vin2)

# ---------------- VIN1: U4.3 -> 3V3_USB (STAIR staircase bit vertex) ----------------
vin1 = [("T", 2, 3.50, 31.04, 3.55, 31.80),
        ("T", 2, 3.55, 31.80, 3.45, 32.90),
        ("T", 2, 3.45, 32.90, 4.30, 33.70)]
job("VIN1", "3V3_USB", vin1)

# ---------------- PR1a: U4.4 -> PR1b component ----------------
pr1a = [("T", 2, 3.00, 31.04, 2.90, 31.70),
        ("T", 2, 2.90, 31.70, 2.85, 33.30),
        ("T", 2, 2.85, 33.30, 2.80, 33.80),
        ("T", 2, 2.80, 33.80, 2.70, 33.95),
        ("V", 2.70, 33.95),
        ("T", 1, 2.70, 33.95, 2.70, 35.30)]
job("PR1a", "PR1", pr1a)

# ---------------- LEG: U2.5 -> 3V3_USB east tree ----------------
leg = [("T", 2, 6.64, 20.50, 7.20, 20.65),
       ("V", 7.20, 20.65),
       ("T", 1, 7.20, 20.65, 7.20, 30.45),
       ("T", 1, 7.20, 30.45, 6.55, 29.70),
       ("V", 6.55, 29.70),
       ("T", 2, 6.55, 29.70, 6.30, 31.30),
       ("T", 2, 6.30, 31.30, 6.45, 33.20),
       ("T", 2, 6.45, 33.20, 6.35, 34.90),
       ("T", 2, 6.35, 34.90, 5.55, 35.10),
       ("T", 2, 5.55, 35.10, 5.55, 36.20),
       ("T", 2, 5.55, 36.20, 6.40, 36.20)]
job("LEG", "3V3_USB", leg)

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.GetZoneList())
b.Save(BASE + "backups/board_route7.kicad_pcb")
print("saved backups/board_route7.kicad_pcb")
