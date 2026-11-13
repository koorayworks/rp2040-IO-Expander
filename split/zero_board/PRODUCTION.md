# Zero側基板 発注用データ

- `gerber/` + `zero_board_gerber.zip`: ガーバー一式（4層、Protel拡張子）とドリル（PTH/NPTH別ファイル）
- `zero_board_bom_jlc.csv`: JLC PCBA用BOM（Comment/Designator/Footprint/LCSC）
- `zero_board_cpl_jlc.csv`: 部品配置（座標は基板左下原点・Y上向き、FH35Cはパッド中心で補正済み）

## バリエーション
- 本データは **表実装版**（FH35C = J3・表面）。裏実装版は BOM/CPL の J3 を J4 に読み替える
  （基板自体は両面にフットプリントがあり、実装しない側はパッドだけ残る）
- J1 は Zero 端子パッド（部品なし）のため BOM/CPL に含めない

## 発注前の残確認
- LCSC番号が未記入の部品（WS2812B-2020、0402の5.1k/100nF）は発注時に照合すること
- FH35C のピン1向きは初回実物で導通確認（逆ならフレキ側の指の並びで吸収、基板は触らない）
