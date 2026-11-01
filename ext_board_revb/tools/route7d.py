import pcbnew, math

BASE = "/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/"
src = open(BASE + "route3.py").read()
head = src.split("# ---------------- grid A*")[0]
head = head.replace('SRC = "backups/board_micro9.kicad_pcb"',
                    'SRC = "%sbackups/board_route7.kicad_pcb"' % BASE)
g = {}
exec(head, g)
b = g["b"]; items = g["items"]; validate = g["validate"]
TM = pcbnew.ToMM; FM = pcbnew.FromMM
LAYV = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

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

# ---- VIN2 v6: B north row y28.95 -> east columns -> C5.1 west edge (8.72,34.90)
job("VIN2", "3V3_BAT", [
    ("T", 2, 3.50, 29.56, 3.55, 28.95),
    ("T", 2, 3.55, 28.95, 5.72, 28.95),
    ("T", 2, 5.72, 28.95, 5.72, 29.85),
    ("T", 2, 5.72, 29.85, 6.40, 29.85),
    ("T", 2, 6.40, 29.85, 6.40, 32.70),
    ("T", 2, 6.40, 32.70, 6.58, 32.70),
    ("T", 2, 6.58, 32.70, 6.58, 33.90),
    ("T", 2, 6.58, 33.90, 7.30, 33.90),
    ("T", 2, 7.30, 33.90, 7.30, 34.90),
    ("T", 2, 7.30, 34.90, 8.72, 34.90)])

# ---- VIN1 v4: pad3 south -> east -> STAIR bit (4.95,31.50)
job("VIN1", "3V3_USB", [
    ("T", 2, 3.50, 31.04, 3.50, 31.90),
    ("T", 2, 3.50, 31.90, 4.60, 31.90),
    ("T", 2, 4.60, 31.90, 4.60, 31.70),
    ("T", 2, 4.60, 31.70, 4.95, 31.50)])

# ---- PR1a v6: U4.4 -> via (4.30,32.70) -> I2 -> PR1b I2 bit (3.90,35.25)
job("PR1a", "PR1", [
    ("T", 2, 3.00, 31.04, 2.80, 31.82),
    ("T", 2, 2.80, 31.82, 3.30, 32.80),
    ("T", 2, 3.30, 32.80, 3.30, 33.30),
    ("T", 2, 3.30, 33.30, 4.30, 32.95),
    ("T", 2, 4.30, 32.95, 4.30, 32.70),
    ("V", 4.30, 32.70),
    ("T", 1, 4.30, 32.70, 4.30, 35.25),
    ("T", 1, 4.30, 35.25, 3.90, 35.25)])

# ---- LEG v8: U2.5 -> via (3.25,20.85) -> I2 maze -> STAIR I2 via (2.80,34.00)
job("LEG", "3V3_USB", [
    ("T", 2, 6.64, 20.50, 3.25, 20.85),
    ("V", 3.25, 20.85),
    ("T", 1, 3.25, 20.85, 4.60, 22.95),
    ("T", 1, 4.60, 22.95, 4.60, 23.45),
    ("T", 1, 4.60, 23.45, 3.75, 23.45),
    ("T", 1, 3.75, 23.45, 3.75, 29.60),
    ("V", 3.75, 29.60),
    ("T", 0, 3.75, 29.60, 2.95, 29.65),
    ("V", 2.95, 29.65),
    ("T", 1, 2.95, 29.65, 2.60, 30.30),
    ("T", 1, 2.60, 30.30, 2.05, 30.30),
    ("T", 1, 2.05, 30.30, 1.90, 34.00),
    ("T", 1, 1.90, 34.00, 2.80, 34.00)])

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
b.Save(BASE + "backups/board_route8.kicad_pcb")
print("saved backups/board_route8.kicad_pcb")
