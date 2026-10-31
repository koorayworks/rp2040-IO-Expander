# REV.A 第3ラウンド（DRCクリーンアップ）進捗メモ

開始点: commit f5bb316。チェックポイント: tools/board_step_r3_start.kicad_pcb

## ベースライン実測（kicad-cli 8.0.9, /tmp/drc_r3_base.json）
- 違反 689件: エラー602（clearance 327, shorting 144, tracks_crossing 63,
  solder_mask_bridge 31, hole_clearance 31, hole_near_hole 6）
  警告87（copper_edge_clearance 34, silk_overlap 15, silk_over_copper 15,
  track_dangling 11, text_height 9, silk_edge_clearance 2, copper_sliver 1）
- 未接続 7件 = すべて GND（うち1件は C2.2+SW_RESET.4 を含む GND 島）
- REV.A (91945d1) 警告ベースライン: 計75（copper_edge 34, silk_overlap 14,
  track_dangling 12, silk_over_copper 9, text_height 4, silk_edge 2）

## ボタン×JLEG 8件の判定 = 実干渉（モデル artifact ではない）
- SW_BOOT パッド (2.66,14.16)/(2.66,17.86) 1.30x1.30 rect と
  JLEG パッド 26/27 (1.33,16.83)/(1.33,14.29) oval 2.60x1.50 PTH が
  F.Cu 上で実重なり（x方向に最大約0.6mm）。SW_RESET 側も同様
  （pad2/3 × JLEG 5/6）。DRC 種別は shorting 4 + mask_bridge 4。
- 両者とも固定条件（ボタン位置=STEP実測、JLEG位置・サイズ）で動かせず、
  製造銅箔同士が実際に触れるため、指示どおり無理に消さず理由つきで残す。
  → 目標は「この8件を除く全エラー 0」。

## 検証済みの見通し
- 「パッド＋GND配線だけでは解けないエラー」は上記8件のみ（実測）。
  残り全エラーは再配線対象のトラック/ビアを含む → 全面引き直しで解消可能。

## 方針（Plan A）
1. 書き出し用コピーで非GND配線を全 rip-up（GND配線/ビアは固定で残す）。
2. SJ ジャンパ脚を疑似ネット化（J4.1+SJ1.2=SJ1L, J4.3+SJ3.2=SJ3L,
   J4.4+SJ4.2=SJ4L）し、ネック3本（SJ1/SJ3/SJ4）も export 側では外す
   （Freerouting がネックをバイパスする太い経路を作るのを防ぐ）。
   SJ6 ネックは GND 固定配線として残る。
   ネック座標（B.Cu, w=0.20）: SJ1 3V3 (7.75,16.95)->(8.70,16.95) /
   SJ3 EX3 (8.15,18.15)->(8.40,18.15) / SJ4 EX4 (8.65,19.35)->(8.95,19.35) /
   SJ6 GND (9.50,20.55)->(10.45,20.55)
3. DSN 書き出し（ルールエリアは export コピーでのみ除去）→ DSN 後編集で
   In1.Cu に GND プレーン（基板矩形）を定義し信号配線を禁止、
   アンテナキープアウト矩形 (4.35,38)-(13.65,43.5) を全層 keepout として注入。
4. Freerouting 2.5.0 で配線 → SES。
5. 元基板へマージ（非GND配線を差し替え、疑似ネットは実ネット名へ戻す）、
   ネック3本を再追加、ゾーン再充填、DRC 実測。
6. gerber/ 再生成、placement.png 再生成、README 更新、ローカル commit。

## ログ
- (開始) ベースライン取得・干渉判定・方針確定まで完了。

## Run 1 failure analysis (2026-10-31)
- FR log "Design Error: Component 'SJ6' pin '10' ... outside board outline at (271200,...)":
  the 4 SJ footprints (empty footprint name) got J6's 10-pin DSN image in
  Freerouting; SJ nets were routed to phantom pins at x=23.7-27.2mm.
  Real SJ pads were not obstacles either -> vias landed on SJ pads
  (bulk of run-1's shorting/mask/hole errors at the SJ cluster).
- KiCad ImportSpecctraSES rejects FR 2.5 SES (returns False, imports
  nothing) -> custom SES parser (tools/r3_ses_parse.py) used instead.
- Fix in prep: unique FPID names (FP_SJ1 etc.) for the 6 empty-named
  footprints in the EXPORT COPY ONLY; SJ6L pseudo-net added
  (J4.6+SJ6.2) with its GND neck/stub removed from the copy.
- Run-1 merged result (241 viol / 150 err / 14 unconnected) DISCARDED.

## VM restart (2026-10-31) - /tmp wiped
- Lost: run-2 SES/DSN, widened/fixed boards w2-w4 (were /tmp-only).
- Survived: tools/board_step_r3_m2.kicad_pcb (run-2 merged+filled board,
  DRC 104 err = 96 width + 8 button, unconnected 8).
- All r3 scripts are in tools/ (workspace). Post-fixes after run 2 were
  deterministic: widen 0.075->0.10; GP24 via -> (14.10,30.72);
  USB_D-_C via (9.28,1.38) + In2 (9.28,1.38)-(8.51,1.38)-(8.51,1.76).
  That sequence reached: errors 8 (button x JLEG only), unconnected 7
  (GND islands only), copper_edge 42 (34 pads + 8 overshoot tracks).
- From now on all intermediates live in tools/r3_work/ (workspace).
- Re-running full pipeline with JLEG-centred prep (run 3).

## 第3ラウンド完了 (2026-10-31)
- 最終基板 ext_board.kicad_pcb: DRC 83件 / エラー8 (ボタンxJLEG 実干渉のみ) / 未接続5 (GND島のみ)
- copper_edge 34 (基準同数)。gerber/ 再生成 (ペースト含む)、placement.png 再生成済み
- チェックポイント: tools/board_step_r3_final.kicad_pcb
- 監査済み: 部品配置・パッドネットは開始点と完全一致、基板外配線なし、SJトポロジ維持
