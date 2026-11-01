import pcbnew, math

BASE = "/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/"
src = open(BASE + "route3.py").read()
head = src.split("# ---------------- grid A*")[0]
head = head.replace('SRC = "backups/board_micro9.kicad_pcb"',
                    'SRC = "%sbackups/board_route7.kicad_pcb"' % BASE)
g = {}
exec(head, g)
b = g["b"]; items = g["items"]; validate = g["validate"]
FM = pcbnew.FromMM
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

# ---- PR1a v12: U4.4 west exit -> east of GPIO28 vertical -> I2 hop -> PR1 I2 bit (3.40,35.00)
job("PR1a", "PR1", [
    ("T", 2, 3.00, 31.04, 2.62, 31.02),
    ("T", 2, 2.62, 31.02, 2.82, 31.35),
    ("T", 2, 2.82, 31.35, 2.82, 32.40),
    ("V", 2.82, 32.40),
    ("T", 1, 2.82, 32.40, 2.30, 33.85),
    ("T", 1, 2.30, 33.85, 2.45, 34.60),
    ("T", 1, 2.45, 34.60, 3.40, 35.00)])

filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
b.Save(BASE + "backups/board_route8.kicad_pcb")
print("saved backups/board_route8.kicad_pcb")
