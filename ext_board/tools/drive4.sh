#!/bin/bash
# Endgame driver: pocket2 over the residue, siblings protected, two passes.
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
for pass in 1 2; do
  echo "== pocket2 pass $pass"
  timeout 1200 python3 -u tools/pocket2.py GPIO7 2>/dev/null | grep -E "OK|FAIL|already|basin"
  timeout 1200 python3 -u tools/pocket2.py GPIO6 GPIO7 2>/dev/null | grep -E "OK|FAIL|already|basin"
  timeout 1200 python3 -u tools/pocket2.py TB2 2>/dev/null | grep -E "OK|FAIL|already|basin"
  timeout 1200 python3 -u tools/pocket2.py TB1 TB2 2>/dev/null | grep -E "OK|FAIL|already|basin"
  for n in GPIO12 EX3 GP17 GP20 GPIO0 GPIO3 GPIO1 GPIO8; do
    timeout 1200 python3 -u tools/pocket2.py "$n" 2>/dev/null | grep -E "OK|FAIL|already|basin"
  done
done
echo "DRIVE4 DONE"
