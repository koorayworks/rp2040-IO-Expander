#!/usr/bin/env python3
"""Rewrite flipped seed nets directly in a saved .kicad_pcb.

This KiCad build writes a few seed items with the wrong
net code (GPIO7's anchor via/track at (10.15,13.75) come
out as GPIO2/net 9 although the in-memory board has them
as GPIO7/net 14; nudging and re-creating do not help).
Fix the file text: parse the net table, find the manifest
items by geometry, rewrite their (net N). Run on the
placement file right after building, before DRC/DSN.
"""
import re, sys

FIXES = [
    # (kind, x, y, layer_name_or_None, wanted_net)
    ('via', 10.15, 13.75, None, 'GPIO7'),
    ('segment', 10.15, 13.75, 'In2.Cu', 'GPIO7'),
]

def main(path):
    txt = open(path).read()
    table = dict((name, int(code)) for code, name
                 in re.findall(r'\(net (\d+) "([^"]+)"\)', txt))
    fixed = 0
    for kind, x, y, layer, want in FIXES:
        want_code = table[want]
        pat = re.compile(r'\(' + kind + r'\s(.*?)\n\t\)', re.S)
        def repl(m):
            nonlocal fixed
            whole = m.group(0)
            blk = m.group(1)
            if layer and f'(layer "{layer}")' not in blk:
                return whole
            pt = re.search(r'\((?:at|start) ([\d.]+) ([\d.]+)\)', blk)
            if not pt or abs(float(pt.group(1)) - x) > 0.01 or abs(float(pt.group(2)) - y) > 0.01:
                return whole
            new_whole, n = re.subn(r'\(net \d+\)', f'(net {want_code})', whole, count=1)
            if n and new_whole != whole:
                fixed += 1
            return new_whole
        txt = pat.sub(repl, txt)
    open(path, 'w').write(txt)
    print(f'fix_seed_nets: rewrote {fixed} items in {path}')

if __name__ == '__main__':
    main(sys.argv[1])
