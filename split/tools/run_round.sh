#!/bin/bash
# usage: run_round.sh GRAFT ROUND PV
source ~/workspace/tools-cache/kicad8-local/env.sh
cd ~/workspace/projects/rp2040-IO-Expander
python3 $1 2>/dev/null
python3 - <<'PYEOF'
import json
p='split/module_board/module_board.kicad_pro'
d=json.load(open(p))
c=d['net_settings']['classes'][0]
c['clearance']=0.10; c['track_width']=0.15; c['via_diameter']=0.40; c['via_drill']=0.20
r=d['board']['design_settings']['rules']
r['min_hole_clearance']=0.20; r['min_through_hole_diameter']=0.20; r['min_via_diameter']=0.40
json.dump(d, open(p,'w'), indent=2)
PYEOF
cp split/module_board/module_board.kicad_pcb split/module_board/backup/placement_$3_round$2seeds.kicad_pcb
(cd split/module_board && kicad-cli pcb drc --output /tmp/drc_r$2p.rpt module_board.kicad_pcb >/dev/null 2>&1)
echo "placement DRC: clearance=$(grep -c '^\[clearance\]' /tmp/drc_r$2p.rpt) shorting=$(grep -c '^\[shorting_items\]' /tmp/drc_r$2p.rpt)"
python3 split/tools/route_prep_module.py 2>/dev/null
cp /tmp/module_board.dsn split/module_board/backup/redo_v$2.dsn
rm -f /tmp/module_board.ses
~/workspace/tools-cache/freerouting-2.5.0-linux-x64/bin/freerouting -de /tmp/module_board.dsn -do /tmp/module_board.ses -mp 150 > split/module_board/backup/redo_route$2.log 2>&1
grep -E "final score" split/module_board/backup/redo_route$2.log
cp /tmp/module_board.ses split/module_board/backup/redo_v$2.ses
cp split/module_board/backup/placement_$3_round$2seeds.kicad_pcb split/module_board/module_board.kicad_pcb
python3 split/tools/route_import_module.py 2>/dev/null
python3 split/tools/patch_module.py 2>/dev/null
cp split/module_board/module_board.kicad_pcb split/module_board/backup/redo_v$2_routed_prefinish.kicad_pcb
(cd split/module_board && kicad-cli pcb drc --output /tmp/drc_r$2.rpt module_board.kicad_pcb >/dev/null 2>&1)
echo "round $2 RESULT: unconnected=$(grep -c '^\[unconnected_items\]' /tmp/drc_r$2.rpt) clearance=$(grep -c '^\[clearance\]' /tmp/drc_r$2.rpt) shorting=$(grep -c '^\[shorting_items\]' /tmp/drc_r$2.rpt)"
grep -A2 unconnected_items /tmp/drc_r$2.rpt | grep -oE '\[(GPIO[0-9]+|EX[0-9]|USB_D\+|3V3_BAT|3V3|GND|STATUS_LED|TB[0-9])\]' | sort | uniq -c
