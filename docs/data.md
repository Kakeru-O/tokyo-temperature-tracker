# データ取得と更新

このプロジェクトでは、気象庁「過去の気象データ」から取得した東京の日別気温データを使います。

## データ出典

- 出典: 気象庁「過去の気象データ」
- 地点: 東京（千代田区・北の丸公園）
- データ種別: 日別値
- 使用項目:
  - 日平均気温
  - 日最高気温
  - 日最低気温

公開・記事化する際は、気象庁データを利用していることを明記します。

## ディレクトリ構成

```text
data/
├── raw/
└── processed/
```

### `data/raw/`

気象庁から取得したCSVをそのまま置きます。

raw CSV は CP932 / Shift_JIS 系の文字コードで、先頭にダウンロード時刻や複数行ヘッダーが含まれます。このディレクトリのファイルは source-only として扱い、分析や dbt では直接使いません。

### `data/processed/`

dbt が読みやすいように整形したCSVを置きます。

主な変換:

- 文字コードを UTF-8 にする
- 複数行ヘッダーを除去する
- 列名を英字に統一する
- 日付列を `YYYY-MM-DD` 形式にする
- 元ファイル名を `source_file` として残す

## 現在のファイル分割

現在は、長期データを複数ファイルに分けて管理しています。

```text
data/raw/jma_tokyo_1926-1950.csv
data/raw/jma_tokyo_1951-1975.csv
data/raw/jma_tokyo_1976-2000.csv
data/raw/jma_tokyo_2001-2025.csv
data/raw/jma_tokyo_20260101-0530.csv
data/raw/jma_tokyo_20260601-0630.csv
```

`data/processed/` にも同じ単位の整形済みCSVがあります。

ファイル名は、対象期間が分かるように `jma_tokyo_YYYY-YYYY.csv` または `jma_tokyo_YYYYMMDD-YYYYMMDD.csv` の形にします。

## データを更新する手順

通常の利用では、`data/processed/` はコミット済みなので再生成不要です。

データを追加・更新する場合だけ、以下の手順を行います。

### 1. 気象庁からCSVを取得する

気象庁「過去の気象データ」から、東京の日別値をCSVで取得します。

取得する項目:

- 平均気温
- 最高気温
- 最低気温

取得したCSVは `data/raw/` に置きます。

例:

```text
data/raw/jma_tokyo_20260601-20261231.csv
```

気象庁CSVは基本的に CP932 / Shift_JIS 系として扱いますが、取得・保存手順によって UTF-8 化されたCSVになる場合があります。`scripts/prepare_processed_jma.py` は CP932 を優先し、読めない場合は UTF-8 として読み込みます。

### 2. processed CSV を再生成する

```bash
uv run python3 scripts/prepare_processed_jma.py
```

このスクリプトは `data/raw/jma_tokyo_*.csv` を読み、同名の整形済みCSVを `data/processed/` に出力します。

### 3. dbt build を実行する

```bash
uv run dbt build --project-dir dbt --profiles-dir dbt
```

dbt は `data/processed/jma_tokyo_*.csv` を入力として、DuckDB に `stg -> int -> mart` の分析テーブルを作ります。

### 4. ノートブックで確認する

```bash
uv run marimo edit main.py
```

## 注意点

### 期間重複

新しい raw CSV を追加するときは、既存ファイルと期間が重複しないようにします。

重複すると `observed_date` の unique test が失敗します。

### 途中年

このプロジェクトには、2026年の途中までのデータが含まれています。

そのため、年次集計では以下が起きます。

- `observed_days` が 365 未満になる
- 6〜8月がまだ存在しない場合、`summer_mean_temp_c` が null になる

dbt tests はこの前提を許容するようにしています。

### 欠測

長期の気象データには欠測が含まれることがあります。

このプロジェクトでは、欠測を無理に補完せず、dbt tests で「現実的な範囲」「日付重複なし」「指標の整合性」を確認する方針です。

## Pages 用CSV

GitHub Pages では DuckDB を直接使いません。

`dbt build` 後に次を実行し、Pages 用CSVを生成します。

```bash
uv run python3 scripts/export_pages_data.py
```

出力先:

```text
data/pages/annual_metrics.csv
data/pages/daily_features.csv
```

`data/pages/` は生成物なのでコミットしません。GitHub Actions で生成し、GitHub Pages の成果物として配信します。
