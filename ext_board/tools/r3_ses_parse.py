#!/usr/bin/env python3
"""Parse a Freerouting SES (KiCad's ImportSpecctraSES rejects the 2.5
dialect) and rebuild its wires/vias on the export board copy.
SES coords are 0.1um units, y negated. Returns counts per layer."""
import pcbnew, re
from collections import Counter

LAYERS = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu,
          "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}

def tokenize(s):
    return re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', s)

def parse(tokens):
    pos = 0
    def rec():
        nonlocal pos
        t = tokens[pos]; pos += 1
        if t == '(':
            out = []
            while tokens[pos] != ')':
                out.append(rec())
            pos += 1
            return out
        return t.strip('"')
    return rec()

def build(board, ses_path):
    tree = parse(tokenize(open(ses_path).read()))
    # find network_out
    def find(node, tag):
        if isinstance(node, list):
            if node and node[0] == tag:
                return node
            for c in node:
                r = find(c, tag)
                if r is not None:
                    return r
        return None
    netout = find(tree, "network_out")
    name2code = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname():
                name2code[p.GetNetname()] = p.GetNetCode()
    stats = Counter(); skipped = Counter(); created = []
    def mm(v): return float(v) / 10000.0
    for netnode in netout[1:]:
        if not (isinstance(netnode, list) and netnode and netnode[0] == "net"):
            continue
        name = netnode[1]
        code = name2code.get(name)
        if code is None:
            skipped[name] += 1
            continue
        for item in netnode[2:]:
            if not isinstance(item, list) or not item:
                continue
            if item[0] == "wire":
                for sub in item[1:]:
                    if isinstance(sub, list) and sub and sub[0] == "path":
                        layer = LAYERS[sub[1]]
                        width = pcbnew.FromMM(mm(sub[2]))
                        pts = [mm(v) for v in sub[3:]]
                        for i in range(0, len(pts) - 2, 2):
                            x1, y1, x2, y2 = pts[i], -pts[i+1], pts[i+2], -pts[i+3]
                            if x1 == x2 and y1 == y2:
                                continue
                            tr = pcbnew.PCB_TRACK(board)
                            tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
                            tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
                            tr.SetWidth(width)
                            tr.SetLayer(layer)
                            tr.SetNetCode(code)
                            board.Add(tr)
                            created.append((name, tr))
                            stats[("track", sub[1])] += 1
            elif item[0] == "via":
                x, y = mm(item[2]), -mm(item[3])
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                via.SetDrill(pcbnew.FromMM(0.20))
                via.SetWidth(pcbnew.FromMM(0.40))
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                via.SetNetCode(code)
                board.Add(via)
                created.append((name, via))
                stats[("via", name)] += 1
    return stats, skipped, created
