# Build JLC CPL + BOM from KiCad POS output.
# Usage: python3 build_cpl_bom.py <pos_file> <board_dir> <board_name> <board_height_mm>
import csv, sys, os
pos_file, bdir, name, H = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
LCSC = {'MDBT50Q-1MV2':'C5118826','TYPE-C-31-M-12':'C165948','USBLC6-2SC6':'C7519',
        'FH35C-31S-0.3SHW':'C424662','TS-1088-AR02016':'C720477'}
COMMENT = {'100n':'100nF','10u':'10uF','5.1k':'5.1k','4.7k':'4.7k','100k':'100k','180k':'180k',
           '2.2uH_2520':'2.2uH shielded 2520','FFC6_TB':'FH12-6S-0.5SH','B2B-PH-K':'B2B-PH-K (THT)',
           'LED_WS2812B-2020_PLCC4_2.0x2.0mm':'WS2812B-2020'}
EXCLUDE = {'zero_board': {'J1','J4'}, 'module_board': {'J2','J5','SJ1','SJ3','SJ4','SJ6','JP1','JP2','JP3','JP4','H1','H2','H3','H4'}}[name]
CENTER_OVERRIDE = {'zero_board': {'J3': (9.00, 11.55)}, 'module_board': {'J1': (9.00, 21.50)}}[name]
rows = []
for line in open(pos_file):
    p = line.split()
    if len(p) < 7 or p[0].startswith('#') or p[0] == 'Ref': continue
    ref, val, pkg = p[0], p[1], p[2]
    x, y, rot, side = float(p[3]), float(p[4]), float(p[5]), p[6]
    if ref in EXCLUDE: continue
    if ref in CENTER_OVERRIDE:
        cx, cy = CENTER_OVERRIDE[ref]; mx, my = cx, H - cy
    else:
        mx, my = x, H + y   # POS y = -design_y  ->  cartesian Y = H - design_y
    rows.append({'ref': ref, 'val': val, 'pkg': pkg, 'x': mx, 'y': my, 'rot': rot, 'side': side})
with open(os.path.join(bdir, name + '_cpl_jlc.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
    for r in rows: w.writerow([r['ref'], f"{r['x']:.3f}", f"{r['y']:.3f}", r['side'], f"{r['rot']:.1f}"])
groups = {}
for r in rows:
    key = (COMMENT.get(r['val'], r['val']), r['pkg'], LCSC.get(r['val'], ''))
    groups.setdefault(key, []).append(r['ref'])
with open(os.path.join(bdir, name + '_bom_jlc.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
    for (comment, pkg, lcsc), refs in sorted(groups.items()):
        w.writerow([comment, ','.join(sorted(refs)), pkg, lcsc])
print(name, 'CPL rows:', len(rows), 'BOM lines:', len(groups))
