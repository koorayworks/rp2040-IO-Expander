#!/usr/bin/env python3
"""Prune tracks that collide with the grafted GPIO3/USB_D+ copper.

Reads a KiCad DRC report; for every [shorting_items]/[clearance]/
[hole_clearance] entry whose two items involve exactly one of the
protected nets (GPIO3, USB_D+) and a Track of another net, delete
that other track from the board. Vias and pads are never deleted.
Iterate with fresh DRC runs until no prunable collision remains.
"""
import os, re, subprocess, sys, pcbnew

ROOT = os.path.expanduser('~/workspace/projects/rp2040-IO-Expander')
DIR = os.path.join(ROOT, 'split', 'module_board')
P = os.path.join(DIR, 'module_board.kicad_pcb')
PRO = os.path.join(DIR, 'module_board.kicad_pro')
PROTECTED = set(sys.argv[1:]) if len(sys.argv) > 1 else {'GPIO3', 'USB_D+'}
mm = pcbnew.FromMM

ITEM_RE = re.compile(
    r'@\(([\d.]+) mm, ([\d.]+) mm\): (Track|Via|Pad) \[([^\]]+)\]')

def reapply_pro():
    import json
    d = json.load(open(PRO))
    d['board']['design_settings']['rules']['min_hole_clearance'] = 0.20
    d['board']['design_settings']['rules']['min_through_hole_diameter'] = 0.20
    d['board']['design_settings']['rules']['min_via_diameter'] = 0.40
    d['net_settings']['classes'][0]['clearance'] = 0.10
    d['net_settings']['classes'][0]['track_width'] = 0.15
    d['net_settings']['classes'][0]['via_diameter'] = 0.45
    d['net_settings']['classes'][0]['via_drill'] = 0.25
    json.dump(d, open(PRO, 'w'), indent=2)

def run_drc(tag):
    rpt = f'/tmp/prune_{tag}.rpt'
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--output', rpt,
                    'module_board.kicad_pcb'],
                   cwd=DIR, capture_output=True)
    return open(rpt).read()

def parse_collisions(text):
    """Return list of (x, y, net) for Tracks to delete."""
    victims = []
    blocks = re.split(r'\n(?=\[)', text)
    for blk in blocks:
        if not blk.startswith(('[shorting_items]', '[clearance]',
                                '[hole_clearance]', '[hole_near_hole]')):
            continue
        items = ITEM_RE.findall(blk)
        if len(items) < 2:
            continue
        nets = {i[3] for i in items}
        if not (nets & PROTECTED):
            continue
        kinds = {i[3]: i[2] for i in items}
        for (x, y, kind, net) in items:
            if kind != 'Track':
                continue
            if net not in PROTECTED:
                victims.append((float(x), float(y), net))
            elif any(k in ('Via', 'Pad') and n != net
                     for (n, k) in kinds.items()):
                # protected track vs another net's via/pad: the
                # track goes (router re-joins the fragments)
                victims.append((float(x), float(y), net))
    return victims

def load_board(path):
    for _ in range(8):
        b = pcbnew.LoadBoard(path)
        if hasattr(b, 'GetFootprints'):
            return b
    raise RuntimeError('LoadBoard kept returning a bad object')

total = 0
for it in range(10):
    b = load_board(P)
    # snapshot: delete victims from previous DRC
    if it > 0:
        pass
    reapply_pro()
    text = run_drc(it)
    victims = parse_collisions(text)
    print(f'iter {it}: prunable collisions -> {len(victims)} tracks')
    if not victims:
        break
    codes = {}
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            try:
                n = pad.GetNet()
                if n and n.GetNetname():
                    codes[n.GetNetname()] = pad.GetNetCode()
            except Exception:
                pass
    n_del = 0
    try:
        tracks = list(b.GetTracks())
    except Exception:
        b = load_board(P)
        tracks = list(b.GetTracks())
    for (x, y, net) in victims:
        for t in tracks:
            try:
                if t.Type() != pcbnew.PCB_TRACE_T:
                    continue
                if t.GetNetCode() != codes.get(net, -1):
                    continue
                sx, sy = pcbnew.ToMM(t.GetStartX()), pcbnew.ToMM(t.GetStartY())
                ex, ey = pcbnew.ToMM(t.GetEndX()), pcbnew.ToMM(t.GetEndY())
            except Exception:
                continue
            if (abs(sx - x) < 0.02 and abs(sy - y) < 0.02) or \
               (abs(ex - x) < 0.02 and abs(ey - y) < 0.02):
                b.Remove(t)
                n_del += 1
                break
    print(f'  deleted {n_del}')
    total += n_del
    pcbnew.SaveBoard(P, b)
print('total deleted:', total)
