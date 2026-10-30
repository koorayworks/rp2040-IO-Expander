#!/bin/bash
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
for n in SWDCLK TB4 GPIO15 GP21 GPIO28 GPIO29 GPIO6 GPIO7 GP17 EX3; do
  echo "--- $n $(date +%H:%M:%S)"
  timeout -k 10 300 python3 -u tools/pocket.py "$n" 2>/dev/null | grep -E ": OK|: FAIL|already|sealed" &
  wait $!
done
echo "DRIVE9 DONE"
