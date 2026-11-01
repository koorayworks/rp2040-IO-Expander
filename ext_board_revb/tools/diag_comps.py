import pcbnew, os, sys
import importlib.util
HERE = os.path.abspath(".")
spec = importlib.util.spec_from_file_location("micro_route", os.path.join(HERE, "micro_route.py"))
mr = importlib.util.module_from_spec(spec); sys.argv = ["diag"]; spec.loader.exec_module(mr)
rt = mr.rt
b = pcbnew.LoadBoard("backups/board_micro5.kicad_pcb")
r = rt.R(b); r.ingest()
r.copper = mr.sample_copper(b, r)
r.pads_copper = [c.copy() for c in r.copper]
r.rebuild_blockers()
# component membership per pad using net_components internals replicated:
import router as R
for name in ("3V3_USB", "3V3_BAT", "BOOST_SW"):
    pads = r.pad_groups[name]
    # monkey: use net_components count + try removing geometry per pad is complex;
    # instead print pad centers and endpoint sizes
    print(name, "comps:", r.net_components(name))
    for i, p in enumerate(pads):
        e = r.endpoint(name, p)
        print(f"  pad{i} ({p['cx']:.2f},{p['cy']:.2f}) endpoint cells:", {L: len(cs) for L, cs in e.items()})
