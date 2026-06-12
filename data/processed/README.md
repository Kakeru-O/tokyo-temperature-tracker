# Processed data (`data/processed/`)

このディレクトリには、`data/raw/` の気象庁CSVを読みやすく整形したファイルを置きます。

取得方法と更新手順は [`docs/data.md`](../../docs/data.md) を参照してください。

## 前提
- 文字コードは `UTF-8`
- 先頭のダウンロード時刻や余計なメタ行は除去済み
- 1ファイル = 1 raw ファイル
- 列名は分析しやすい英字名に統一

## 想定カラム
1. `date`
2. `avg_temp_c`
3. `avg_quality`
4. `avg_homogenization`
5. `max_temp_c`
6. `max_quality`
7. `max_homogenization`
8. `min_temp_c`
9. `min_quality`
10. `min_homogenization`
11. `source_file`

## 使い方
- DuckDB と dbt はこのディレクトリを入力として扱います
- raw の再加工が必要になったら、`scripts/prepare_processed_jma.py` を再実行します
