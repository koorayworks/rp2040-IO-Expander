#!/usr/bin/env python3
"""USB_VBUS: route_net commits successful legs even when the net as a
whole fails; save unconditionally so repeated runs converge leg by leg."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("router", os.path.join(HERE, "router.py"))
rt = importlib.util.module_from_spec(spec)
sys.argv = ["vbus"]
spec.loader.exec_module(rt)
PATH = os.path.expanduser("~/workspace/projects/rp2040-IO-Expander/ext_board/ext_board.kicad_pcb")

def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    name = "USB_VBUS"
    before = r.net_components(name)
    print("components before:", before, flush=True)
    ok = r.route_net(name, via_cost=2.0, max_exp=700000)
    after = r.net_components(name)
    pcbnew.SaveBoard(PATH, b)
    print(f"route_net ok={ok} components {before} -> {after}", flush=True)

if __name__ == "__main__":
    main()
