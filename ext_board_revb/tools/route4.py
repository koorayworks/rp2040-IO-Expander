import sys, traceback
src = open("route3.py").read()
head = src.split("JOBS = [")[0]
head = head.replace('SRC = "backups/board_micro9.kicad_pcb"', 'SRC = "backups/board_stripped.kicad_pcb"')
head = head.replace('if pd["multi"] or l in pd["lay"]:', 'if l in pd["lay"]:')
g = {}
exec(head, g)
do_job = g["do_job"]; b = g["b"]
import pcbnew
W1 = (1.5,12.0,27.5,38.5)
JOBS4 = [
 ("VOUT7", "3V3", (4.00,29.56,2), W1),
 ("VOUT2", "3V3", (4.00,31.04,2), W1),
 ("VIN1", "3V3_USB", (3.50,31.04,2), (1.5,8.0,27.5,34.0)),
 ("VIN2", "3V3_BAT", (3.50,29.56,2), W1),
 ("PR1a", "PR1", (3.00,31.04,2), (1.5,9.0,27.5,38.5)),
 ("PR1b", "PR1", (5.00,35.58,2), (1.5,9.0,27.5,38.5)),
 ("STAIR", "3V3_USB", (4.80,29.05,2), (1.5,10.0,27.5,38.5)),
 ("LEG", "3V3_USB", (6.64,20.50,2), (0.3,17.7,16.0,38.5)),
]
results = {}
for (name, net, start, win) in JOBS4:
    try:
        results[name] = do_job(name, net, start, win)
    except Exception as e:
        print(name, "EXCEPTION:", repr(e)); traceback.print_exc()
        results[name] = "EXC"
    sys.stdout.flush()
    filler = pcbnew.ZONE_FILLER(b); filler.Fill(b.Zones())
    b.Save("backups/board_route4.kicad_pcb")
    print("checkpoint saved after", name, "->", results[name]); sys.stdout.flush()
print("RESULTS:", results)
