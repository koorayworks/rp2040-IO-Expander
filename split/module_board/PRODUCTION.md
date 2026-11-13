# モジュール側基板 発注用データ

- `gerber/` + `module_board_gerber.zip`: ガーバー一式（4層、Protel拡張子）とドリル（PTH/NPTH別ファイル）
- `module_board_bom_jlc.csv`: JLC PCBA用BOM（Comment/Designator/Footprint/LCSC）
- `module_board_cpl_jlc.csv`: 部品配置（座標は基板左下原点・Y上向き、FH35Cはパッド中心で補正済み）

## バリエーション
- 本データは **表実装版**（FH35C = J1・表面）。裏実装版は BOM/CPL の J1 を J2 に読み替える
- BOM/CPL に含めないもの: J5（SWDパッド）、SJ1/SJ3/SJ4/SJ6・JP1〜JP4（はんだジャンパ＝基板上の
  パターン、部品なし）、H1〜H4（M2取り付け穴）

## 発注前の残確認（重要）
- **U3 (TPS610994) / U4 (TPS2116) のフットプリント実寸と L1 (2.2uH) の接続を、発注前に
  データシートで再照合すること**（REV.B から引き継いだ未確認事項）
- LCSC番号が未記入の部品が多い（電源IC類・FH12・B2B-PH-K・CAS-120A・AO3401・受動部品）。
  発注時に LCSC/JLC ライブラリで照合して埋めること
- J6 (B2B-PH-K) はスルーホール部品。JLC の THT 対応可否を発注時に確認すること
- SW3 (CAS-120A) の ON 方向は実物で確認すること
- MDBT50Q はブートローダ未書き込みで納品される前提（初回のみ SWD から書き込みが必要）
