#!/bin/bash
# Endgame driver v6: pocket3 pass, wallpocket pass, pocket3 pass.
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
list_nets() {
  kicad-cli pcb drc --format json -o /tmp/drc_drive.json ext_board.kicad_pcb >/dev/null 2>&1
  python3 - <<'EOF'
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
EOF
}
for phase in pocket3a wallpocket pocket3b; do
  NETS=$(list_nets)
  echo "== $phase targets: $NETS"
  if [ -z "$NETS" ]; then echo "ALL SIGNAL NETS CONNECTED"; break; fi
  for n in $NETS; do
    if [ "$phase" = "wallpocket" ]; then
      timeout 1200 python3 -u tools/wallpocket.py "$n" >> tools/drive6_detail.log 2>&1
    else
      timeout 1200 python3 -u tools/pocket3.py "$n" >> tools/drive6_detail.log 2>&1
    fi
    tail -1 tools/drive6_detail.log | grep -E "OK|FAIL|already" || true
  done
done
echo "DRIVE6 DONE"
