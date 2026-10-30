#!/bin/bash
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
for n in GPIO14 TB6 GP17 GP20 EX3 GPIO12 GPIO0 GPIO3 GPIO6 GPIO7; do
  echo "--- $n $(date +%H:%M:%S)"
  timeout 900 python3 -u tools/pocket3.py "$n" 2>/dev/null | grep -E ": OK|: FAIL|already|basin"
done
echo "DRIVE8 DONE"
