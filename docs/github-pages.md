# GitHub Pages での公開

このプロジェクトでは、marimo の WebAssembly HTML export を使って、GitHub Pages 上でノートブックを動かします。

## 方針

GitHub Pages 上では、dbt や DuckDB をブラウザ内で実行しません。

代わりに、GitHub Actions で次の処理を行います。

```text
dbt build
  -> DuckDB に mart / int テーブルを作成
  -> Pages 用CSVへ export
  -> marimo WebAssembly HTML を生成
  -> GitHub Pages へ deploy
```

ブラウザでは、dbt で作成済みのCSVを Polars で読み込みます。

## なぜ WASM 版にするのか

静的HTMLとしてグラフを貼るだけなら簡単ですが、それでは BI ツールやノートブックの通常エクスポートと大きく変わりません。

marimo WebAssembly 版では、サーバーなしの GitHub Pages 上で Python が動きます。Polars でデータを処理し、Altair でグラフを再描画できるため、読者がブラウザ上で年や指標を選びながら探索できます。

## Pages 用データ

Pages 用のCSVは、`dbt build` 後に DuckDB から書き出します。

```bash
uv run python3 scripts/export_pages_data.py
```

出力:

```text
data/pages/annual_metrics.csv
data/pages/daily_features.csv
```

`data/pages/` は生成物なのでコミットしません。GitHub Actions の中で生成し、`site/` にコピーして配信します。

## ローカルで Pages 版を確認する

```bash
uv run dbt build --project-dir dbt --profiles-dir dbt
uv run python3 scripts/export_pages_data.py
uv run marimo export html-wasm main.py -o site --mode run --no-show-code
mkdir -p site/data/pages
cp data/pages/*.csv site/data/pages/
cd site
python3 -m http.server
```

ブラウザで開きます。

```text
http://localhost:8000
```

CSVが配信されているか確認したい場合:

```text
http://localhost:8000/data/pages/annual_metrics.csv
```

ブラウザによってはCSVが表示ではなくダウンロードされます。それでも配信自体はできています。

## GitHub Actions

Pages デプロイは `.github/workflows/pages.yml` で行います。

主なステップ:

1. `uv sync --locked`
2. `uv run dbt build --project-dir dbt --profiles-dir dbt`
3. `uv run python3 scripts/export_pages_data.py`
4. `uv run marimo export html-wasm main.py -o site --mode run --no-show-code`
5. `data/pages/*.csv` を `site/data/pages/` にコピー
6. `site/` を GitHub Pages にデプロイ

## 実装上の注意

### WASM では `src/analysis.py` を import しない

ローカル実行では `src/analysis.py` から DuckDB を読みます。

一方、WASM 実行ではローカルの `src/analysis.py` は存在しないため、`ModuleNotFoundError` を検知したら Pages 用CSVを読むようにしています。

### CSVはHTTPで読む

WASM 内の Python から `pl.read_csv("data/pages/annual_metrics.csv")` と書くと、ブラウザ上のURLではなく Pyodide の仮想ファイルシステムを探すことがあります。

そのため、Pages 版では `urllib.request.urlopen()` でHTTP取得し、`io.BytesIO` 経由で Polars に渡しています。

### 相対パスに注意する

Web Worker の位置によって、相対パスの基準がページとずれることがあります。

このプロジェクトでは、次の候補を順に試してCSVを取得します。

```text
data/pages/...
./data/pages/...
../data/pages/...
/data/pages/...
```

CSVではなくHTMLが返ってきた候補はスキップします。
