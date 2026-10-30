#!/bin/bash
# Driver v2: DRC -> unrouted non-GND nets -> stub.py per net -> repeat.
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
for iter in 1 2 3 4; do
  kicad-cli pcb drc --format json -o /tmp/drc_drive.json ext_board.kicad_pcb >/dev/null 2>&1
  NETS=$(python3 - <<'EOF'
import json, re
from collections import OrderedDict
d = json.load(open("/tmp/drc_drive.json"))
nets = OrderedDict()
for it in d["unconnected_items"]:
    for im in it["items"]:
        m = re.search(r"\[([^\]]+)\]", im["description"])
        if m and m.group(1) not in ("GND", "USB_VBUS"):
            nets[m.group(1)] = True
print(" ".join(nets.keys()))
EOF
)
  echo "== iter $iter unrouted: $NETS"
  if [ -z "$NETS" ]; then echo "ALL SIGNAL NETS CONNECTED"; break; fi
  for n in $NETS; do
    timeout 900 python3 -u tools/stub.py "$n" 2>/dev/null | grep -E "OK|FAIL|already|sacrificed"
  done
done
echo "DRIVE2 DONE"
