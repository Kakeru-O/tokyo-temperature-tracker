# dbt の役割

このプロジェクトでは、東京（千代田区・北の丸公園）の日別気温データをもとに、暑さの変化を可視化します。

可視化そのものは `main.py` の marimo ノートブックで行いますが、ノートブックの中で複雑な集計ロジックを直接書きすぎると、指標の意味や品質チェックが見えにくくなります。

そこで、このプロジェクトでは dbt を使って、可視化の前段にあるデータ変換を管理しています。

## dbt とは

dbt は、SQL で書いたデータ変換を、ソフトウェア開発のように管理するためのツールです。

主な役割は次の通りです。

- SQL の変換処理をモデルとして分ける
- モデル同士の依存関係を `ref()` で管理する
- `stg -> int -> mart` のような層構造を作る
- データ品質テストを実行する
- ドキュメントや定義を YAML に残す

このプロジェクトでは dbt-duckdb を使い、DuckDB に分析用テーブルを作っています。

## このプロジェクトの流れ

全体の流れは次の通りです。

```text
data/raw
  -> scripts/prepare_processed_jma.py
  -> data/processed
  -> dbt build
  -> tokyo_temperature.duckdb
  -> main.py
```

各ステップの役割は次の通りです。

- `data/raw/`
  - 気象庁から取得した元CSV
- `scripts/prepare_processed_jma.py`
  - raw CSV の文字コードやヘッダーを整える
- `data/processed/`
  - dbt が読みやすい形にしたCSV
- `dbt/`
  - SQLで変換・集計するレイヤー
- `tokyo_temperature.duckdb`
  - dbt build で作られるローカルの分析DB
- `main.py`
  - dbt が作ったテーブルを読み、marimo + Polars + Altair で可視化する

## dbt モデル構成

dbt モデルは、用途ごとに3層に分けています。

```text
stg
  -> int
  -> mart
```

### stg

`stg` は staging の略です。

元データを分析しやすい列名・型・粒度に整える層です。ここでは、日付や気温列を整え、夏日・真夏日・猛暑日・熱帯夜のフラグを作っています。

代表モデル:

- `stg_jma_tokyo_daily_temperature`

### int

`int` は intermediate の略です。

可視化や mart を作る前の中間集計を置く層です。日別特徴量、年次集計、夏の始まり・終わり、熱帯夜の連続日数などを作っています。

代表モデル:

- `int_tokyo_daily_temperature_features`
- `int_tokyo_annual_temperature`
- `int_tokyo_summer_timing`
- `int_tokyo_tropical_night_streaks`
- `int_tokyo_monthly_temperature`

### mart

`mart` は、ノートブックや記事で直接使うための最終テーブルです。

代表モデル:

- `mart_tokyo_temperature_story_metrics`
- `mart_tokyo_temperature_anomalies`

`main.py` は、ローカル実行時にこの mart / int テーブルを読みます。

## なぜノートブックに直接書かないのか

ノートブックだけでも集計はできます。

ただし、すべてをノートブックに書くと、次の問題が出やすくなります。

- 指標定義がUIコードに埋もれる
- 集計ロジックの再利用がしづらい
- データ品質チェックを忘れやすい
- GitHub Pages 用データを作る導線が弱くなる
- 記事で「この数字はどう作ったのか」を説明しづらい

dbt に変換ロジックを寄せることで、ノートブックは「探索と表現」に集中できます。

## dbt tests

dbt tests は、データが期待した条件を満たしているかを確認する仕組みです。

このプロジェクトでは、次のようなテストを定義しています。

- 主キーが重複していないこと
- 必須列が null でないこと
- 月が 1〜12 の範囲にあること
- 通算日が 1〜366 の範囲にあること
- 気温が現実的な範囲にあること
- `最高気温 >= 最低気温` が成り立つこと
- 夏日・真夏日・猛暑日・熱帯夜フラグが気温閾値と一致すること
- 年間の夏日数・真夏日数・猛暑日数の大小関係が崩れていないこと
- 夏の期間が初日・最終日から計算した値と一致すること

テストは `dbt build` でモデル作成と一緒に実行されます。

```bash
uv run dbt build --project-dir dbt --profiles-dir dbt
```

## GitHub Pages との関係

GitHub Pages 上では、dbt や DuckDB をブラウザ内で動かしません。

代わりに、GitHub Actions で次の処理を行います。

```text
dbt build
  -> mart / int テーブルを作成
  -> Pages 用CSVへ export
  -> marimo WebAssembly HTML を生成
  -> GitHub Pages へデプロイ
```

ブラウザ版の marimo は、dbt で作成済みのCSVを Polars で読み込みます。

つまり Pages 版でも、データの定義や集計は dbt が担当しています。ブラウザでは、その結果をインタラクティブに探索します。

## ローカルでの実行手順

```bash
uv sync
uv run dbt build --project-dir dbt --profiles-dir dbt
uv run marimo edit main.py
```

データを raw CSV から再生成したい場合だけ、次を実行します。

```bash
uv run python3 scripts/prepare_processed_jma.py
```
