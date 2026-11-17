# 初回発注手順（6セット分、2026-11-17 方針）

構成: Zero 基板 10枚（実装6）／モジュール基板 10枚（実装6、U1 抜き）／
フレキ 10枚／MDBT50Q-1MV2 ×7（スイッチサイエンス、別途購入・手実装）。
データは全て **表実装版**（FH35C を表面に実装する版）。

発注は4件: JLC に3件（Zero PCBA／モジュール PCBA／フレキ FPC）＋
スイッチサイエンスに1件。JLC の3件はカートにまとめて発送すると
送料を節約できる場合がある。

## 1. モジュール基板（JLC PCBA）

1. jlcpcb.com にログイン → 「Order Now」→ `split/module_board/module_board_gerber.zip` をアップロード
2. 基板仕様: 4層／板厚 1.6mm／銅箔 1oz（自動検出と一致を確認）
   - **表面処理: ENIG**（未指定だと HASL になる。必ず変更）
   - マスク色: 任意
   - **数量: 10**
3. PCB Assembly を ON:
   - PCBA Type: **Standard**（両面実装のため Economic 不可）
   - Assembly Side: **Both Sides**
   - **PCBA Qty: 6**
4. BOM／CPL アップロード（**必ず noU1 版**）:
   - `module_board_bom_jlc_noU1.csv`
   - `module_board_cpl_jlc_noU1.csv`
5. 部品マッチング画面で確認:
   - 全行が LCSC コードと一致してマッチすること（U1 の行は無いのが正解）
   - J6（B2B-PH-K、THT）が実装対象として認識されること
   - CPL プレビューで **SW3 が裏面・回転 -90°** になっていることを目視確認
6. 注文確定・支払い

## 2. Zero 基板（JLC PCBA）

1. `split/zero_board/zero_board_gerber.zip` をアップロード
2. 基板仕様: 4層／板厚 1.6mm／銅箔 1oz
   - **表面処理: ENIG**
   - **Castellated Holes: Yes**（J1 の端子穴が基板端にかかる形状のため必須）
   - マスク色: 任意
   - **数量: 10**
3. PCB Assembly ON: Standard／Both Sides／**PCBA Qty: 6**
4. BOM／CPL は通常版（U1 のような抜きはなし）:
   - `zero_board_bom_jlc.csv`
   - `zero_board_cpl_jlc.csv`
5. マッチング画面で全行マッチを確認して確定

## 3. フレキ（JLC FPC、実装なし）

1. FPC の発注フローで `split/flex/flex_gerber.zip` をアップロード
2. 指定:
   - 基材: ポリイミド／**1層**
   - FPC 厚さ: **0.11mm**
   - 表面処理: ENIG（FPC 標準）
   - カバーレイ: 黄（標準）・表面のみ
   - **Gold Fingers: Yes、厚み 0.2mm**
   - 補強板: ポリイミド／裏面／両端 2.85mm ゾーン
   - **数量: 10**
3. プレビューで補強板（`flex_100mm-pib_0.1.gbr`）が両端に認識されて
   いることを目視確認。フォームの計算で補強板の厚みが 0.1mm 以外に
   なったら、その厚みに合わせてファイル名を変えた zip が必要
   （`flex/PRODUCTION.md` 参照）

## 4. MDBT50Q-1MV2（スイッチサイエンス）

- 商品: nRF52840 MDBT50Q-1MV2 モジュール（チップアンテナ）
  https://www.switch-science.com/products/5529
- ¥1,287（税込）× **7個**（6セット分＋手実装の予備1）= ¥9,009＋送料
- 在庫86（2026-11-17 確認）。技適マークあり
- 到着後、モジュール基板へ手実装。ブートローダ未書き込みのため
  初回は J5 から SWD で書き込む

## 到着後の確認（初回実物）

- フレキの嵌合（FH35C へ無理なく入るか）と合計厚 0.2±0.03 の実測
- フレキ経由の全チャンネル導通（ピン1向きの最終確認）
- Zero の USB-C 前後位置と本物 Zero との嵌合
- モジュール手実装 → SWD 書き込み → 実機動作
