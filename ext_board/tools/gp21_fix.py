#!/usr/bin/env python3
"""GP21 targeted fix: try sacrifices GP19, GP20, GP23, GP22 (in that order).
For each: rip sacrifice, route GP21; then route sacrifice. If sacrifice
fails, restore its original objects and restore GP21's absence (rip GP21).
Saves only when BOTH are connected."""
import pcbnew, os, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fix4", os.path.join(HERE, "fix4.py"))
f4 = importlib.util.module_from_spec(spec)
sys.argv = ["gp21_fix"]
spec.loader.exec_module(f4)
f1 = f4.f1
rt = f4.rt
PATH = f4.PATH


def main():
    b = pcbnew.LoadBoard(PATH)
    r = rt.R(b)
    r.ingest()
    f4.patch_track_relaxed(r)
    name = "GP21"
    print("GP21 components at start:", r.net_components(name), flush=True)
    for blk in ["GP19", "GP20", "GP23", "GP22"]:
        if r.net_components(name) <= 1:
            break
        if blk not in r.geom:
            continue
        saved = list(r.geom[blk]["objects"])
        r.ripup(blk)
        t0 = time.time()
        ok = f4.route(r, name) and r.net_components(name) <= 1
        print(f"rip {blk}: GP21 route {'OK' if ok else 'fail'} ({time.time()-t0:.0f}s)", flush=True)
        if not ok:
            if name in r.geom:
                r.ripup(name)
            f4.restore(r, blk, saved)
            continue
        t0 = time.time()
        ok2 = f4.route(r, blk) and r.net_components(blk) <= 1
        print(f"  re-route {blk}: {'OK' if ok2 else 'fail'} ({time.time()-t0:.0f}s)", flush=True)
        if ok2:
            pcbnew.SaveBoard(PATH, b)
            print("SAVED: GP21 +", blk, "connected", flush=True)
            return
        # sacrifice could not come back: undo both, restore original
        if blk in r.geom:
            r.ripup(blk)
        if name in r.geom:
            r.ripup(name)
        f4.restore(r, blk, saved)
        print(f"  {blk} could not return; restored original", flush=True)
    print("GP21 components at end:", r.net_components(name), flush=True)


if __name__ == "__main__":
    main()
