# tokyo-temperature-tracker

東京（千代田区・北の丸公園）の日別気温データを使って、暑さの変化を可視化するプロジェクトです。

ローカルでは dbt + DuckDB で作成した分析テーブルを、marimo ノートブックから Polars / Altair で可視化します。GitHub Pages では、dbt で事前生成したCSVを marimo WebAssembly 版で読み込み、ブラウザだけでインタラクティブに動かします。

## Stack

- marimo
- Polars
- Altair
- DuckDB
- dbt / dbt-duckdb
- GitHub Pages / WebAssembly

## Quick Start

```bash
uv sync
uv run dbt build --project-dir dbt --profiles-dir dbt
uv run marimo edit main.py
```

`main.py` が本番用の marimo ノートブックです。ローカルでは `dbt build` によって作られる `tokyo_temperature.duckdb` の `mart` / `int` テーブルを読みます。

## Data

データ出典:

- 気象庁「過去の気象データ」
- 地点: 東京（千代田区・北の丸公園）
- 粒度: 日別値
- 項目: 日平均気温、日最高気温、日最低気温

このリポジトリでは、取得したCSVを以下の2層で管理しています。

- `data/raw/`
  - 気象庁から取得したCSVをそのまま配置
- `data/processed/`
  - dbt が読みやすいように UTF-8 / 英字列名へ整形したCSV

`data/processed/` はコミット済みなので、通常の利用ではデータ前処理を再実行する必要はありません。データ取得方法と更新手順は [docs/data.md](docs/data.md) にまとめています。

## dbt

dbt は `data/processed/` から DuckDB 上に `stg -> int -> mart` の分析テーブルを作ります。

```bash
uv run dbt debug --project-dir dbt --profiles-dir dbt
uv run dbt build --project-dir dbt --profiles-dir dbt
```

dbt の役割、モデル構成、テスト内容は [docs/dbt.md](docs/dbt.md) にまとめています。

## Notebook

```bash
uv run marimo edit main.py
```

ノートブックでは、年別推移、選択年の日別推移、ランキング、期間比較を確認できます。

## GitHub Pages

GitHub Pages では、ブラウザ上で dbt や DuckDB を動かしません。GitHub Actions で dbt を実行し、Pages 用CSVを生成してから marimo WebAssembly HTML と一緒にデプロイします。

ローカルで Pages 版を確認する場合:

```bash
uv run python3 scripts/export_pages_data.py
uv run marimo export html-wasm main.py -o site --mode run --no-show-code
mkdir -p site/data/pages
cp data/pages/*.csv site/data/pages/
python3 -m http.server --directory site 
```

ブラウザで `http://localhost:8000` を開きます。

詳しい構成は [docs/github-pages.md](docs/github-pages.md) にまとめています。

## Repository Layout

```text
.
├── data/
│   ├── raw/
│   └── processed/
├── dbt/
│   ├── models/
│   ├── macros/
│   ├── dbt_project.yml
│   └── profiles.yml
├── docs/
├── scripts/
├── src/
├── main.py
├── pyproject.toml
└── uv.lock
```

## Generated Files

以下は生成物なのでコミットしません。

- `tokyo_temperature.duckdb`
- `data/pages/`
- `site/`
- `dbt/target/`
- `dbt/dbt_packages/`
- `dbt/logs/`
