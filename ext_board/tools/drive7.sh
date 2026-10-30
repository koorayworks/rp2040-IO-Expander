#!/bin/bash
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
list_nets() {
  kicad-cli pcb drc --format json -o /tmp/drc_drive.json ext_board.kicad_pcb >/dev/null 2>&1
  python3 - <<'PYEOF'
import json, re
from collections import OrderedDict
d = json.load(open("/tmp/drc_drive.json"))
nets = OrderedDict()
for it in d["unconnected_items"]:
    for im in it["items"]:
        m = re.search(r"\[([^\]]+)\]", im["description"])
        if m and m.group(1) != "GND":
            nets[m.group(1)] = True
print(" ".join(nets.keys()))
PYEOF
}
NETS=$(list_nets)
echo "== pocket v1 pass: $NETS"
for n in $NETS; do
  timeout 600 python3 -u tools/pocket.py "$n" >> tools/drive7_detail.log 2>&1
  grep -E ": OK|: FAIL|already" tools/drive7_detail.log | tail -1
done
NETS=$(list_nets)
echo "== wallpocket pass: $NETS"
for n in $NETS; do
  timeout 900 python3 -u tools/wallpocket.py "$n" >> tools/drive7_detail.log 2>&1
  grep -E ": OK|: FAIL|already" tools/drive7_detail.log | tail -1
done
echo "DRIVE7 DONE"
