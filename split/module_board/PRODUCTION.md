# モジュール側基板 発注用データ

- `gerber/` + `module_board_gerber.zip`: ガーバー一式（4層、Protel拡張子）とドリル（PTH/NPTH別ファイル）
- `module_board_bom_jlc.csv`: JLC PCBA用BOM（Comment/Designator/Footprint/LCSC）
- `module_board_cpl_jlc.csv`: 部品配置（座標は基板左下原点・Y上向き、FH35Cはパッド中心で補正済み）

## バリエーション
- 本データは **表実装版**（FH35C = J1・表面）。裏実装版は BOM/CPL の J1 を J2 に読み替える
- BOM/CPL に含めないもの: J5（SWDパッド）、SJ1/SJ3/SJ4/SJ6・JP1〜JP4（はんだジャンパ＝基板上の
  パターン、部品なし）、H1〜H4（M2取り付け穴）

## 改訂（2026-11-13 夜・外部精査を受けて再出力）
- **電池監視を分圧化**: MDBT50Q pin12 (P0.31/AIN7) への VBAT 直結をやめ、
  R11/R12 = 1M/1M 分圧（新ネット VBAT_SENSE、0603）を追加。詳細は
  MODULE_PINMAP.md の電源節。DRC は修正前と同条件で未接続0・交差5のまま、
  shorting は意図的ジョイント6件のみ（JP3 の PU_EX2↔EX2 を含む。
  pre/post で基板銅は不変だが DRC の数え方が 5→6 に揺れたもの）
- R11/R12 の courtyard が互いに重なる指摘が1件ある（部品間隔が詰まった
  配置のため。本基板には同種の既存指摘が多数あり、実装可否は発注時に確認）

## データシート照合（2026-11-13 実施済み）
- **U3 (TPS610994, TI SLVSD88)**: ピン配置は全て一致（1=GND、2=VOUT、3=FB→GND が
  固定3.3V版の正規接続、4=EN→VBAT、5=SW、6=VIN、7 EP=GND）。フットプリントは
  KiCad 標準 DFN-6-1EP（WSON 2×2mm）で問題なし
- **U4 (TPS2116, TI SLVSFG1A)**: ピン配置は全て一致（1=GND、2/7=VOUT、3=VIN1、
  4=PR1、5=MODE→VIN1 で優先モード、6=VIN2、8=ST 未接続）。ランド寸法は TI の
  Land Pattern Example と完全一致（パッド 0.67×0.3、ピッチ 0.5、列間 1.48）
- **L1 の接続ミスを発見・修正済み**: 当初 pad2 が出力側 (3V3_BAT) に繋がっていたが、
  データシートの Pass-Through 記述（入力→インダクタ→整流素子→出力）どおり
  入力側 (VBAT) が正解。pad2 のネットを VBAT へ付け替え、3V3_BAT 側はブリッジで
  再接続。修正後 DRC は未接続0・クリアランス0（控え: backup/pre_lfix_20261113）
- **C5 を 22µF に変更**: 昇圧出力コンデンサはデータシート最小 20µF (公称) のため、
  10µF×1 では不足。フットプリント (0603) はそのまま BOM の値を変更

## 発注前の残確認
- LCSC番号が未記入の部品が多い（電源IC類・FH12・B2B-PH-K・AO3401・受動部品）。
  発注時に LCSC/JLC ライブラリで照合して埋めること
- J6 (B2B-PH-K) はスルーホール部品。JLC の THT 対応可否を発注時に確認すること
- SW3 (PCM12SMTR) の ON 方向は実物で確認すること
- SW3 は裏面実装かつ回転 -90° のため、発注時に JLC の CPL プレビューで
  SW3 の向き（pin1 マークと BAT+ = pin3 の対応）を必ず目視確認すること
- MDBT50Q はブートローダ未書き込みで納品される前提（初回のみ SWD から書き込みが必要）

## SW3 変更（2026-11-14）

- SW3 を CAS-120A → C&K PCM12SMTR（0.3A、LCSC C221841、JLC Extended）へ変更し、
  ガーバー/BOM/CPL を再出力済み。詳細は ROUTING_STATUS.md の同日節を参照
- 控え: backup/pre_sw3fix_20261114.kicad_pcb / backup/final_sw3fix_20261114.kicad_pcb
