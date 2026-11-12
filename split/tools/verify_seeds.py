#!/usr/bin/env python3
"""Verify seed items keep their nets through SaveBoard.

This KiCad build flips some items' nets on save depending
on position (found 2026-11-12, round 30: vias at
(10.04,13.823)/(4.8,18.6)/(10.35,18.6) came back as
GPIO2/SWDCLK/GPIO1). Build in memory, save, reload, and
check every manifest entry against the reloaded board.
Exit 1 if any mismatch or missing item.
"""
import os, sys, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
TMP = '/tmp/verify_seeds.kicad_pcb'
mm = pcbnew.ToMM

VIAS = [
    ((7.85, 19.05), 'GPIO3'), ((7.85, 18.35), 'GPIO13'),
    ((8.58, 15.98), 'GPIO4'), ((9.6, 19.0), 'GPIO5'),
    ((8.87, 15.36), 'GPIO5'), ((9.0, 19.2), 'GPIO5'),
    ((10.15, 13.75), 'GPIO7'), ((6.7, 20.75), 'GPIO15'),
    ((11.96, 13.158), 'GPIO15'), ((6.3, 21.1), 'GPIO0'),
    ((14.35, 15.7), 'GPIO10'), ((5.15, 22.8), 'GPIO28'),
    ((5.45, 19.3), 'STATUS_LED'),
    ((10.5, 18.45), 'GPIO11'), ((11.85, 18.75), 'GPIO27'),
    ((12.2, 21.0), 'USB_D-'), ((13.45, 19.25), 'GND'),
    ((5.05, 21.2), 'GPIO27'), ((8.669, 14.379), 'GPIO2'),
    ((9.4, 13.75), 'GPIO6'),
]
TRACK_STARTS = [
    ((11.96, 13.158), 2, 'GPIO15'), ((10.55, 16.0), 2, 'GPIO15'),
    ((10.75, 16.95), 2, 'GPIO15'),
    ((10.15, 13.75), 2, 'GPIO7'), 
    ((8.669, 14.379), 1, 'GPIO2'), ((8.669, 14.379), 2, 'GPIO2'),
    ((8.87, 15.36), 1, 'GPIO5'), ((8.87, 15.36), 2, 'GPIO5'),
    ((8.58, 15.98), 1, 'GPIO4'), ((8.58, 15.98), 2, 'GPIO4'),
    ((13.88, 25.74), 1, 'EX5'),
    ((6.6, 19.925), 0, 'GPIO15'), ((6.9, 22.075), 31, 'GPIO0'),
    ((5.7, 22.075), 0, 'GPIO28'),
]

g = {}
exec(open(os.path.join(ROOT, 'split', 'tools', 'build_module.py')).read(), g)
pcbnew.SaveBoard(TMP, g['board'])
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_seed_nets
fix_seed_nets.main(TMP)
b = pcbnew.LoadBoard(TMP)

bad = 0
for (x, y), want in VIAS:
    hit = None
    for t in b.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            p = t.GetPosition()
            if abs(mm(p.x) - x) < 0.01 and abs(mm(p.y) - y) < 0.01:
                hit = t.GetNetname()
    if hit != want:
        print(f'VIA FLIP/MISSING ({x},{y}): want {want}, got {hit}')
        bad += 1
for (x, y), layer, want in TRACK_STARTS:
    hit = None
    for t in b.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            continue
        s = t.GetStart()
        if abs(mm(s.x) - x) < 0.01 and abs(mm(s.y) - y) < 0.01 and t.GetLayer() == layer:
            hit = t.GetNetname()
    if hit != want:
        print(f'TRACK FLIP/MISSING ({x},{y}) L{layer}: want {want}, got {hit}')
        bad += 1
print('seed check:', 'ALL OK' if bad == 0 else f'{bad} BAD')
sys.exit(1 if bad else 0)
