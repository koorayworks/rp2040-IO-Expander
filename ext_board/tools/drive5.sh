#!/bin/bash
cd ~/workspace/projects/rp2040-IO-Expander/ext_board || exit 1
for n in GPIO6 TB2 TB1 GPIO12 EX3 GP17 GP20 GPIO0 GPIO3 GPIO1 GPIO8 GPIO7; do
  timeout 1500 python3 -u tools/pocket3.py "$n" 2>/dev/null | grep -E "OK|FAIL|already|basin"
done
echo "DRIVE5 DONE"
