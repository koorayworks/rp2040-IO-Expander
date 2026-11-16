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
- **2026-11-16 追記**: 独立監査で判明した SW3 周辺の干渉（SWDIO の穴切断、
  GPIO29 のタブ経由ショート、R11/R12 パッド欠け、GPIO11 の穴切断ほか）を
  修正し、ガーバー/BOM/CPL を再出力済み。詳細は ROUTING_STATUS.md の
  2026-11-16 節を参照。発注はこの再出力版で行うこと

## シルク追加（2026-11-16）

MODULE_PINMAP／PINMAP_EXT が謳う基板シルク2件を追加（gr_text のみ、銅・部品は不変、
DRC 全カテゴリ不変、Gerber 再出力済み、BOM/CPL 差分なし）:

- 電池警告（F.SilkS、基板東端の空き帯）: `BAT: DRY CELL 1-3.3V` /
  `NO LiPo/LFP NO CHARGE`
- FFC#2 切替表（B.SilkS、基板北端の空き領域）: `SJ1 3V3>EX1` /
  `SJ3 EX3>GND` / `SJ4 EX4>3V3` / `SJ6 GND>EX6` / `FFC2 DEF=UNI ALT=TPS43`

文字高は 0.8mm（線幅 0.15mm）。基板が高密度で J6／J4 近傍には判読可能な
文字が入る空きがなく（実測で最大でも約2.5×1.8mm）、配置は同一面内の最大の
空き領域とした。文書側の「J4 脇」「J6 の近く」の文言とはズレが残る点に注意。
控え: backup/pre_silk_20261116.kicad_pcb

## 発注画面での指定（2026-11-16 最終監査対応）

- 層数 4層／板厚 1.6mm／銅箔 1oz（基板データと一致する標準値）
- **表面処理は ENIG を指定すること**（未指定だと HASL になる。0.3mm ピッチの
  FH35C や微細パッドがあるため平坦な ENIG が前提）
- マスク色は任意
- PCBA は両面実装。発注時の残確認（LCSC 照合、J6 の THT 実装可否、SW3 の
  CPL 目視確認、C5 の型番指定、U3 EP のステンシル開口）は本文の各節を参照

## LCSC 記入状況（2026-11-16 調査）

全17行中14行を製品ページで確認して BOM に記入済み（受動部品・電源 IC・
J6・D1 等。詳細な型番対応は git 履歴と同日の監査記録を参照）。
個別の決定・注意:

- **Q1 は AO3401A（C15127、AOS 後継品・Basic）へ変更**。無印 AO3401 の
  AOS 名義品は LCSC になく、リテラル一致品は二社品で仕様が劣るため。
  ピン互換・スペックは AO3401A が上位
- **J6 (B2B-PH-K) の THT 実装は JLC のサービス対象**であることを部品
  ページと公式ブログで確認（Wave Soldering、Economic／Standard）。
  追加料金・配置制約の可能性はあるため BOM マッチング画面で最終確認
- C5 (22µF) は Samsung CL10A226MQ8NRNC（C59461、6.3V）。0603 の 22µF は
  市販品の定格が実質 6.3V 上限で 10V 品は存在しない。3.3V レールでは
  定格内だが DC バイアスで実効容量は公称を下回る前提で使うこと
- 10µF は C96446（Samsung 25V）。在庫表示に揺れがあり、代替は C19702

**未確定（BOM 空欄のまま）**:
- **U3 TPS610994DRVR**: JLC/LCSC の実装ライブラリに該当品なし（DSBGA 版と
  可変版・固定3.6V版のみ存在）。対応は本人の判断待ち（Global Sourcing／
  Mouser 等で購入し手実装／TPS61099 可変版への設計変更）
- **J3/J4 FH12-6S-0.5SH(55)**: JLC ライブラリにリスティングを確認できず。
  U3 と同様の対応（取り寄せ or 手実装）が要る
- L1 2.2µH 2520 シールド: 候補型番は実在（TDK TFM252012ALVA2R2MTAA 等）
  だが LCSC コード未確認。発注画面の部品検索で型番照合する想定
