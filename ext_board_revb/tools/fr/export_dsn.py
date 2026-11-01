import pcbnew, json, collections
SRC = "/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/backups/board_route5.kicad_pcb"
DSN = "/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/fr/board.dsn"
b = pcbnew.LoadBoard(SRC)
# snapshot of existing copper items for later diff
snap = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        snap.append(("V", t.GetNet().GetNetname(), round(pcbnew.ToMM(t.GetPosition().x),4), round(pcbnew.ToMM(t.GetPosition().y),4)))
    else:
        snap.append(("T", t.GetNet().GetNetname(), t.GetLayerName(),
                     round(pcbnew.ToMM(t.GetStart().x),4), round(pcbnew.ToMM(t.GetStart().y),4),
                     round(pcbnew.ToMM(t.GetEnd().x),4), round(pcbnew.ToMM(t.GetEnd().y),4)))
json.dump(snap, open("/home/hatch/workspace/projects/rp2040-IO-Expander/ext_board_revb/tools/fr/snap_route5.json","w"))
print("snapshot items:", len(snap))
ok = pcbnew.ExportSpecctraDSN(b, DSN)
print("DSN export:", ok)
