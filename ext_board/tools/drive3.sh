#!/bin/bash
# Driver v3 (pocket): DRC -> unrouted non-GND nets -> pocket.py per net.
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
for iter in 1 2 3; do
  kicad-cli pcb drc --format json -o /tmp/drc_drive.json ext_board.kicad_pcb >/dev/null 2>&1
  NETS=$(python3 - <<'EOF'
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
)
  echo "== iter $iter unrouted: $NETS"
  if [ -z "$NETS" ]; then echo "ALL SIGNAL NETS CONNECTED"; break; fi
  for n in $NETS; do
    timeout 900 python3 -u tools/pocket.py "$n" 2>/dev/null | grep -E "OK|FAIL|already|sealed"
  done
done
echo "DRIVE3 DONE"
