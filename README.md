# tokyo-temperature-tracker

東京（千代田区・北の丸公園）の長期気温データを使って、暑さの変化を可視化します。

## Stack
- DuckDB
- dbt (dbt-duckdb)
- Polars
- Altair
- marimo


## Data
- Raw CSV is stored in `data/raw/` as-is (tracked, source-only).
- Cleaned CSVs live in `data/processed/` and are the input used by DuckDB / dbt.
- Source: 気象庁「過去の気象データ」（東京 / 北の丸公園、日別値、気温: 日平均・最高・最低）。

## Data prep
1. `uv run python3 scripts/prepare_processed_jma.py`
   - `data/raw/` のCSVを読み、文字コードとヘッダーを整えて `data/processed/` に書き出します
2. `uv sync`
   - 依存関係を反映します

## dbt (host with uv)
`dbt/` にプロジェクトと `profiles.yml`（DuckDB 接続設定）があります。

実行例:
1. `uv sync`
   - `pyproject.toml` の依存（`dbt-duckdb`, `duckdb`, `polars`, `marimo`, `altair`）をインストールします
2. `cd dbt && uv run dbt debug`
   - DuckDB の接続やプロジェクト設定が正しいか確認します
3. `cd dbt && uv run dbt build`
   - `data/processed/ -> stg -> int -> mart` を作成し、テストも実行します

## Notebook
```bash
uv run marimo edit main.py
```

`main.py` が本番用の marimo ノートブックです。dbt で作成した DuckDB の mart / intermediate テーブルを優先して読み、存在しない場合は `data/processed/` のCSVから直接読み込みます。
