# Round 5 progress — reconnect C1 pad2 [GND]

Start: local commit `9951201` (R4 final). DRC errors 0, warnings 70
{copper_edge_clearance 34, silk_overlap 14, silk_over_copper 11,
text_height 9, silk_edge_clearance 2}; unconnected 6 = 5 GND zone
island pairs + C1 pad2 [GND] island (the R4 leftover). User decision
2026-10-31: C1 area may be unfrozen (C1 move/rotation + local re-route
around C1/C2/U2); everything else stays frozen.

## Environment note
- This VM's KiCad had been rolled back to 7.0.11 (cannot open the 8.0
  file). Restored 8.0.9 first via `~/workspace/tools-cache/restore_kicad.sh`
  (cached debs), same procedure as previous rounds.

## Method
- Solver `tools/r5_solve.py` on top of router.py's 0.05mm raster model
  (the same clearance model that produced the DRC-clean R3/R4 boards):
  base grids built from a copy with C1 and the two old USB_VBUS B.Cu
  stub segments removed; scan C1 transforms (dx, dy in ±2.0mm step 0.2,
  4 pad configurations EW/NS) with pad copper+halo tests, courtyard
  tests, GND-via existence, then full A* for the GND stub (multi-target:
  any via-legal cell) and the VBUS re-feed.
- Calibration notes (raster is a pruning model; kicad-cli DRC is the
  oracle): pad halo grow had to be 0.05, not 0.10 — the raster already
  inflates foreign copper (bbox pads, 0.08-radius track stamps), and a
  full 0.10 grow rejects even the known-clean start position (C1 pad2
  halo contains 8 foreign cells at (0,0) on the start board).
  Also: courtyard test must use JLEG per-pad bboxes; the JLEG
  pads-union fallback bbox spans the whole board edge and blocks
  everything.

## Key finding
- R4 concluded "no legal bridge exists" with JLEG pad9 treated as a
  stadium centred on its hole (14.08, 21.96). The pad's REAL copper
  bbox is x 13.33-14.83, y 21.16-23.76: the castellation shape is
  offset +0.5mm south of the hole centre. That opens a via-sized
  pocket south-east of C1 pad2, between the GP21 In2 diagonal,
  the GP24 B.Cu run, and pad9's true copper edge.

## Solution (C1 NOT moved — sanctioned unfreeze turned out unnecessary)
- Add GND via (14.85, 20.55), 0.40/0.20 (same spec as all board vias).
- Add B.Cu tracks w=0.10: C1 pad2 centre (14.175, 19.90) ->
  (14.55, 20.30) -> (14.80, 20.55) -> via centre (14.85, 20.55).
- Nothing else changed: all 24 footprints identical to start
  (pos/rot/flipped/pad nets+positions, audited against
  tools/r5_start_audit.json); VBUS feed untouched.

## Build gotcha
- pcbnew `LoadBoard` of the tools/ snapshot (no sibling .kicad_pro)
  substitutes DEFAULT project design settings, and `SaveBoard` then
  writes those defaults out next to the target — a trial build scored
  878 phantom DRC errors (via_diameter/drill_out_of_range on every
  existing via) from this alone. `tools/r5_build.py` therefore loads
  the board from the destination path pre-populated with the start
  board + the real ext_board.kicad_pro. APPLY mode asserts the real
  board is still byte-identical to the start snapshot first.

## Final state (2026-10-31, kicad-cli 8.0.9, verified on the real file)
- **DRC violations 70, ALL warnings, errors 0** — every warning type
  exactly at the start count (no increases, no new types).
- **Unconnected 5** = the GND zone island pairs only. C1 pad2 [GND]
  reconnected (via -> In1 GND plane). Signal unconnected 0 (as before).
- Audit: PASS (only the added via + 3 track segments differ).
- gerber/ regenerated with tools/plot_gerbers.py (paste included) +
  `kicad-cli pcb export drill` (hole count 153 -> 154, exactly the new
  via); ext_board-job.gbrjob unchanged, as in previous rounds.
  placement.png regenerated (tools/make_diagram.py).
- Checkpoints: tools/board_step_r5_start.kicad_pcb,
  tools/board_step_r5_final.kicad_pcb.
- Scripts: tools/r5_solve.py, tools/r5_build.py,
  tools/r5_solutions.json, tools/r5_start_audit.json.
