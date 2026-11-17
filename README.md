# Wireless Split-Keyboard Module (RP2040-Zero footprint)

A two-board module set that replaces the RP2040-Zero on a split keyboard
and makes the **whole keyboard wireless**: the connection to the PC
(Bluetooth LE) and the left–right link both run on the module board's
nRF52840.

- **Zero board** (`split/zero_board/`): same outline and pinout as a real
  RP2040-Zero (18.0 × 23.5 mm). It is a passive pass-through — no MCU on it.
- **Module board** (`split/module_board/`): carries a Raytac MDBT50Q
  (nRF52840) plus the power circuitry. 18 × 36 mm, 4-layer.
- **Flex** (`split/flex/`): custom 100 mm FPC joining the two boards,
  Hirose FH35C-31S-0.3SHW(50) connectors on both ends, 30 of 31 channels
  used. Pin map: `split/FFC_PINMAP_30P.md` (channel numbers are defined
  by the module-board pads).

## Status — read this first

**Design complete and independently audited. NOT fabricated and NOT
tested on real hardware.**

The design went through several blind audit rounds against primary
sources (datasheets, manufacturer drawings, STEP models). Every defect
found was fixed before fabrication: an unconnected USB VBUS net, an open
flex lane, a connector pin-1 orientation error, sub-spec trace widths.
DRC on the final data: 0 unconnected nets, 0 clearance violations on both
boards. But no physical board has ever been made, so fit (flex mating,
total thickness 0.2 ± 0.03 mm, USB-C position vs. a real Zero) and
electrical behaviour on real hardware are **unverified**. Build at your
own risk; a first article check is strongly recommended.

Manufacturing was planned and fully costed, then shelved: at small lots
the set cannot be produced near the intended price (see
`split/PRICING.md`). The design is released as open hardware instead.

## Power

- Battery: **dry cells, 1–3.3 V input. No LiPo / LiFePO4, no charging.**
- TPS2116 power mux (USB vs. battery), TPS61099 boost to ~3.31 V
  (576k/249k divider), TPS7A2033 LDO.
- MDBT50Q-1MV2 and -P1MV2 share the same footprint and pinout; either
  can be fitted (both TELEC certified).

## Ordering / assembly notes

- Full step-by-step: `split/ORDER_GUIDE.md`; per-board details in each
  board's `PRODUCTION.md`.
- JLCPCB, 4-layer, 1.6 mm, ENIG. Standard PCBA (parts on both sides).
- The Zero board needs the **Castellated Holes** option enabled.
- **U1 (MDBT50Q) is not stocked by JLC.** Use the `*_noU1` BOM/CPL
  variants and hand-mount U1 afterwards. The module ships without a
  bootloader: first flash is via SWD on J5.
- Firmware must set: LFRC `K32SRC_RC` + `K32SRC_500PPM`,
  `CONFIG_GPIO_AS_PINRESET=y`, SAADC acquisition time 40 µs.

## Repository layout

| Path | Contents |
|---|---|
| `SPLIT_SPEC.md` | Frozen specification of the current design |
| `split/zero_board/` | Zero board: KiCad, Gerber zip, BOM/CPL, PRODUCTION.md |
| `split/module_board/` | Module board: KiCad, Gerber zip, BOM/CPL (incl. noU1), PRODUCTION.md |
| `split/flex/` | Flex FPC: generator script, Gerber zip, PRODUCTION.md |
| `split/FFC_PINMAP_30P.md` | The frozen 30-channel pin assignment |
| `split/ORDER_GUIDE.md` | Ordering procedure (6-set first run) |
| `split/PRICING.md` | Cost model and why it was not sold |
| everything at repo root outside `split/` | **Legacy** earlier generations (Rev.W, ext_board). Not the current design. |

## Summary for AI agents

- project: wireless conversion module set for split keyboards (RP2040-Zero replacement)
- form_factor: drop-in replacement for RP2040-Zero (18.0 x 23.5 mm)
- boards: zero_board (passive pass-through), module_board (18 x 36 mm), flex FPC 100 mm
- layers: 4 (both boards), flex 1-layer polyimide
- mcu_module: Raytac MDBT50Q-1MV2 or -P1MV2 (nRF52840), hand-mounted
- connector: Hirose FH35C-31S-0.3SHW(50), 30 channels, pinmap in split/FFC_PINMAP_30P.md
- radio: Bluetooth LE via nRF52840 (host connection and inter-half link)
- power: dry-cell 1-3.3 V in, TPS2116 mux, TPS61099 boost ~3.31 V, TPS7A2033 LDO; no charging
- status: design_complete=true, audited=true, fabricated=false, hardware_tested=false
- manufacturer: JLCPCB PCBA (Standard, both sides), ENIG, castellated holes on zero board
- licence: CERN-OHL-S v2

## Licence

CERN Open Hardware Licence v2 — Strongly Reciprocal (CERN-OHL-S).
See `LICENSE`. If you make and distribute products from this design,
your modified source must stay open under the same licence.
