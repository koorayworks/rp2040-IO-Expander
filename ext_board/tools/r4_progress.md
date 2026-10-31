# Round 4 progress — switch swap to clear button x JLEG shorts

Start: local commit `5c8e651` (R3 final). DRC 83 = errors 8
(shorting 4 + mask_bridge 4, all SW_BOOT/SW_RESET pads vs JLEG
castellation) + warnings {silk_overlap 15, silk_over_copper 15,
text_height 9, copper_edge 34, silk_edge 2}; unconnected 5 (GND zone
island pairs only). User decision 2026-10-31: smaller switch
(3x4.65mm class), keep centres at STEP-measured positions.

## Part selection
- Old BOM part TS-1187A-B-A-B (LCSC C318884) verified as a real
  5.1x5.1mm switch — the interference was real, not a footprint error.
- Chosen: **XUNPU TS-1088-AR02016** (LCSC/JLC C720477, JLC Basic;
  stock 2026-10-31: LCSC ~219,950 / JLC $0.0529-). Body 3.9-4.0 (long
  axis) x 2.9-3.0 x H2.0mm, 2-terminal SPST (no internal pad pairs —
  pad1 = signal, pad2 = GND). Suffix R = NO locating post
  (C variant needs a 0.75mm hole — rejected).
- Datasheet (XUNPU TS-1088 official PDF via LCSC C720477) recommended
  land: 2 pads 1.35 (pitch dir) x 1.80, pitch 4.15, no holes.
  LCEDA library SW-SMD_L3.9-W3.0-P4.45 uses pitch 4.45 — disagrees
  with the manufacturer drawing; manufacturer value 4.15 adopted.
- Final pads CUSTOM 0.85 x 1.45 at local (0, +/-2.075): width 1.80
  would hit the USB_VBUS F.Cu run x=5.3 (BOOT side) and the GP22 via
  (14.2625,18.5694) (RESET side); height 1.80 would crowd the GPIO4
  via. Area = 51% of recommended, but the terminal foot contact band
  (+/-1.60..2.40 from centre) is fully inside the pad span
  [1.35, 2.80]. Documented in README (design note 13).
- SW_RESET footprint rotated 180 deg so both switches follow
  pad1 = signal / pad2 = GND. Centres kept EXACTLY:
  SW_BOOT (4.51,16.01), SW_RESET (13.51,16.01).
- JLEG clearance (final board, effective copper shapes):
  BOOT pad west edge 4.085 vs JLEG east edge 2.130 -> **1.955mm**;
  RESET pad east edge 13.935 vs JLEG west edge 15.870 -> **1.935mm**.
  (Nominal-bbox conservative estimate: 1.455 / 1.435mm.) >> 0.10 req.

## Gotcha found en route
- pcbnew `PAD.SetPosition` and `PCB_SHAPE.SetStart/SetEnd` take BOARD
  coordinates and convert to footprint-local. r4_swap passed local
  coords for shapes -> all switch silk/fab/courtyard graphics were
  displaced by exactly the footprint position (silk_edge_clearance
  2 -> 3 exposed it). Fixed in r4_fix12 by re-setting shapes in the
  board frame; stored locals now match intent ((+/-1.45, -/+2) etc.).

## Local re-routes (clearance-legal, rules 0.10/0.10 unchanged)
- BOOT: new F/B hop west of the switch (vias (3.30,13.90),
  (6.70,13.80)); GND side reuses via (4.15,16.85).
- RESET: pure F.Cu path east of pad1 via the restored R3 corridor
  x=15.667-15.678 into the existing south chain; GND via (13.3,13.0).
- GPIO2: In2 dive at (12.85,17.30)-(12.70,17.85), via, F column x=12.70.
- USB_D-: R3 In2 diagonal restored, via (5.06,16.90), F column x=5.12
  then x=5.30 down to the existing via (5.4906,24.3847).
- TB3: via (3.30,14.60), F column x=3.16.
- GPIO0: via_top moved to (13.22,16.15); B.Cu tail re-shaped;
  via_bot at (13.62,20.72) with F stub onto the south chain start
  (13.3712,20.7954). (The (13.37,20.35) candidate sits inside the
  GPIO6/GPIO7 In2 diagonal band — sums 33.33/33.80 fence it.)
- GND C2 stitch: B.Cu detours all dead-ended (EX4 wall x=10.7225,
  EX5 via (11.3613,19.3136), VBUS via (11.8707,19.4926), SJ6 pad3).
  Solved with a GND via at (11.40,18.0328) — exactly on the In2 GND
  chain segment (10.5536,17.1864)-(12.258,18.8908) — plus a short
  B.Cu track into C2 pad2.
- C1 pad2 [GND]: bridge proven impossible (fenced by VBUS via,
  C1 pad1, C2 pad2, GPIO4 via, EX6 via, GP21 In2 diagonal, JLEG
  pad9 stadium). Left as a pour island; rationale in README note 13.

## Final state (2026-10-31, kicad-cli 8.0.9)
- **DRC violations 70, ALL warnings, errors 0**:
  silk_overlap 14 (<=15), silk_over_copper 11 (<=15), text_height 9,
  copper_edge_clearance 34 (=), silk_edge_clearance 2 (=).
- **Unconnected 6** = 5 GND zone-island pairs (same as start) +
  C1 pad2 island. Signal unconnected 0. C2 pad2 reconnected.
- gerber/ regenerated incl. paste + Excellon drill; placement.png
  regenerated; BOM + README updated; checkpoint
  tools/board_step_r4_final.kicad_pcb.
- Scripts: tools/r4_swap.py, r4_fix1_pads.py ... r4_fix12.py.
