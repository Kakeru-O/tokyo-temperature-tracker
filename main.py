#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair>=6.1.0",
#     "duckdb>=1.4.0",
#     "marimo>=0.23.8",
#     "polars>=1.36.0",
# ]
# ///

import marimo

__generated_with = "0.23.9"
app = marimo.App(width="full")


@app.cell
def _():
    import importlib
    import io
    import sys
    import urllib.request
    from datetime import date, timedelta
    from math import isnan
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    import altair as alt
    import marimo as mo
    import polars as pl

    def is_wasm_runtime():
        app_object = getattr(mo, "app", None)
        is_wasm = getattr(app_object, "is_wasm", None)
        if callable(is_wasm):
            return bool(is_wasm())
        return False

    running_in_wasm = is_wasm_runtime()

    SERIES_COLORS = {
        "年平均気温": "#1f77b4",
        "6-8月平均気温": "#ff7f0e",
        "夏日(最高25℃以上)": "#2ca02c",
        "真夏日(最高30℃以上)": "#d62728",
        "猛暑日(最高35℃以上)": "#8c564b",
        "熱帯夜(最低25℃以上)": "#9467bd",
        "夏日の初日": "#2ca02c",
        "真夏日の初日": "#d62728",
        "熱帯夜の初日": "#9467bd",
        "夏日の期間": "#2ca02c",
        "真夏日の期間": "#d62728",
    }

    def period_slice(df, y0, y1):
        start_year = min(y0, y1)
        end_year = max(y0, y1)
        return df.filter(pl.col("year").is_between(start_year, end_year))

    def format_float(value, digits):
        return f"{value:.{digits}f}"

    def difference(left, right, digits):
        return f"{right - left:+.{digits}f}"

    def day_of_year_to_month_day(value):
        if value is None:
            return "-"
        if isinstance(value, float) and isnan(value):
            return "-"
        target_date = date(2004, 1, 1) + timedelta(days=int(round(float(value))) - 1)
        return target_date.strftime("%m/%d")

    def build_metric_table(rows, left_label, right_label):
        return pl.DataFrame(rows, schema=["指標", left_label, right_label, "差分(後-前)"], orient="row")

    def build_timing_table(rows, left_label, right_label):
        return pl.DataFrame(
            rows,
            schema=[
                "指標",
                f"{left_label} (通算日)",
                f"{left_label} (月日)",
                f"{right_label} (通算日)",
                f"{right_label} (月日)",
                "差分(後-前)",
            ],
            orient="row",
        )

    try:
        import analysis
    except ModuleNotFoundError:
        analysis = None
        running_in_wasm = True

    if running_in_wasm or analysis is None:
        def read_pages_csv(path):
            data = None
            attempted_urls = []
            candidate_urls = [
                path,
                f"./{path}",
                f"../{path}",
                f"/{path}",
            ]
            for url in candidate_urls:
                attempted_urls.append(url)
                try:
                    with urllib.request.urlopen(url) as response:
                        candidate_data = response.read()
                except Exception:
                    continue

                if (
                    candidate_data.lstrip().startswith(b"<!DOCTYPE")
                    or candidate_data.lstrip().startswith(b"<html")
                ):
                    continue

                data = candidate_data
                break

            if data is None:
                raise FileNotFoundError(
                    "Pages 用CSVを取得できませんでした。CSVではなくHTMLが返った可能性があります。試したURL: "
                    + ", ".join(attempted_urls)
                )

            return pl.read_csv(io.BytesIO(data), try_parse_dates=True)

        def load_metrics():
            return read_pages_csv("data/pages/annual_metrics.csv")

        def load_daily_data():
            return read_pages_csv("data/pages/daily_features.csv")
    else:
        analysis = importlib.reload(analysis)
        SERIES_COLORS = analysis.SERIES_COLORS
        build_metric_table = analysis.build_metric_table
        build_timing_table = analysis.build_timing_table
        day_of_year_to_month_day = analysis.day_of_year_to_month_day
        difference = analysis.difference
        format_float = analysis.format_float
        load_daily_data = analysis.load_daily_data
        load_metrics = analysis.load_metrics
        period_slice = analysis.period_slice
    return (
        SERIES_COLORS,
        alt,
        build_metric_table,
        build_timing_table,
        day_of_year_to_month_day,
        difference,
        format_float,
        load_daily_data,
        load_metrics,
        mo,
        period_slice,
        pl,
    )


@app.cell
def _(load_daily_data, load_metrics, pl):
    # 年次指標と日次データを読み込み、以降の集計はPolarsを主役にする。
    annual = load_metrics().with_columns(pl.col("year").cast(pl.Int64))
    daily = load_daily_data().with_columns(
        pl.col("year").cast(pl.Int64),
        pl.col("observed_date").cast(pl.Date),
    )

    # martにないイベント境界を、日次データから補完する。
    def event_bounds(condition, prefix):
        bounds = (
            daily.filter(condition)
            .group_by("year")
            .agg(
                pl.col("dayofyear").min().alias(f"first_{prefix}_dayofyear"),
                pl.col("dayofyear").max().alias(f"last_{prefix}_dayofyear"),
            )
        )
        return bounds.with_columns(
            (
                pl.col(f"last_{prefix}_dayofyear")
                - pl.col(f"first_{prefix}_dayofyear")
                + 1
            ).alias(f"{prefix}_span")
        )

    supplemental_bounds = [
        event_bounds(pl.col("max_temp_c") >= 35, "extreme_hot"),
        event_bounds(pl.col("min_temp_c") >= 25, "tropical_night"),
    ]
    annual = annual.drop(
        [
            "first_extreme_hot_dayofyear",
            "last_extreme_hot_dayofyear",
            "extreme_hot_span",
            "first_tropical_night_dayofyear",
            "last_tropical_night_dayofyear",
            "tropical_night_span",
        ],
        strict=False,
    )
    for bounds in supplemental_bounds:
        annual = annual.join(bounds, on="year", how="left")
    return annual, daily


@app.cell
def _(annual, mo):
    start_year = int(annual["year"].min())
    end_year = int(annual["year"].max())
    year_options = [str(year) for year in annual["year"].to_list()]

    # 全体で見る対象期間。終了年は次のセルで、開始年以降だけに絞る。
    target_start_year = mo.ui.dropdown(
        year_options,
        value=str(start_year),
        label="対象開始年",
    )
    return end_year, start_year, target_start_year, year_options


@app.cell
def _(end_year, mo, target_start_year, year_options):
    valid_target_end_options = [
        year for year in year_options if int(year) >= int(target_start_year.value)
    ]
    target_end_year = mo.ui.dropdown(
        valid_target_end_options,
        value=str(end_year),
        label="対象終了年",
    )

    target_controls = mo.hstack(
        [target_start_year, target_end_year],
        gap=2,
        justify="start",
    )
    return target_controls, target_end_year


@app.cell
def _(annual, daily, pl, target_end_year, target_start_year):
    # UI側で終了年を開始年以降に絞っているので、ここではそのまま期間化する。
    target_start = int(target_start_year.value)
    target_end = int(target_end_year.value)

    # 対象期間の抽出はPolarsで行う。
    filtered_annual = annual.filter(pl.col("year").is_between(target_start, target_end))
    filtered_daily = daily.filter(pl.col("year").is_between(target_start, target_end))
    return filtered_annual, filtered_daily, target_end, target_start


@app.cell
def _(mo, pl):
    def value_text(value, unit="", digits=0):
        if value is None:
            return "-"
        return f"{float(value):.{digits}f}{unit}"

    def rank_position(frame, metric, year, ascending):
        valid = frame.drop_nulls([metric])
        if valid.is_empty() or year not in set(valid["year"].to_list()):
            return "-"
        rank = (
            valid.with_columns(
                pl.col(metric).rank(method="min", descending=not ascending).alias("rank")
            )
            .filter(pl.col("year") == year)
            .select("rank")
            .item()
        )
        return f"{int(rank)}位"

    def stat_card_html(cards):
        card_html = "\n".join(
            f"""
            <section class="story-stat-card" style="--accent: {card['color']};">
              <div class="story-stat-label">{card['label']}</div>
              <div class="story-stat-value">{card['value']}</div>
              <div class="story-stat-caption">{card['caption']}</div>
            </section>
            """
            for card in cards
        )
        return mo.Html(
            f"""
            <style>
              .story-stat-grid {{
                display: grid;
                gap: 12px;
                grid-template-columns: repeat(2, minmax(180px, 1fr));
              }}
              .story-stat-card {{
                background: #ffffff;
                border: 1px solid color-mix(in srgb, var(--accent) 24%, #d9e1df);
                border-left: 5px solid var(--accent);
                border-radius: 8px;
                box-shadow: 0 8px 22px rgba(22, 36, 45, 0.08);
                color: #1e2a2f;
                min-height: 106px;
                padding: 14px 16px;
              }}
              .story-stat-label {{
                color: #5a6970;
                font-size: 13px;
                font-weight: 700;
              }}
              .story-stat-value {{
                color: #16242d;
                font-size: 28px;
                font-weight: 800;
                line-height: 1.2;
                margin-top: 8px;
              }}
              .story-stat-caption {{
                color: #68787f;
                font-size: 12px;
                margin-top: 8px;
              }}
              @media (max-width: 760px) {{
                .story-stat-grid {{
                  grid-template-columns: 1fr;
                }}
              }}
            </style>
            <div class="story-stat-grid">{card_html}</div>
            """
        )

    return rank_position, stat_card_html, value_text


@app.cell
def _(
    SERIES_COLORS,
    alt,
    filtered_annual,
    mo,
    pl,
    target_controls,
    target_end,
    target_start,
):
    # 年平均と夏季平均を同じチャートで比較できるように縦持ちへ変換する。
    annual_long = filtered_annual.unpivot(
        index=["year"],
        on=["annual_mean_temp_c", "summer_mean_temp_c"],
        variable_name="series",
        value_name="temp_c",
    ).with_columns(
        pl.col("series").replace(
            {
                "annual_mean_temp_c": "年平均気温",
                "summer_mean_temp_c": "6-8月平均気温",
            }
        )
    )

    # marimo が選択状態を読み取れるよう、Altair の selection には明示名を付ける。
    year_selection = alt.selection_point(
        name="selected_year_point",
        fields=["year"],
        empty=True,
        clear="dblclick",
    )

    x_domain = (
        [target_start - 1, target_end + 1]
        if target_start == target_end
        else [target_start, target_end + 1]
    )

    annual_chart = (
        alt.Chart(annual_long)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "year:Q",
                title="年",
                axis=alt.Axis(format="d"),
                scale=alt.Scale(domain=x_domain),
            ),
            y=alt.Y("temp_c:Q", title="気温(℃)", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "series:N",
                title="系列",
                scale=alt.Scale(
                    domain=["年平均気温", "6-8月平均気温"],
                    range=[
                        SERIES_COLORS["年平均気温"],
                        SERIES_COLORS["6-8月平均気温"],
                    ],
                ),
            ),
            opacity=alt.condition(year_selection, alt.value(1.0), alt.value(0.32)),
            tooltip=[
                alt.Tooltip("year:Q", title="年", format="d"),
                alt.Tooltip("series:N", title="系列"),
                alt.Tooltip("temp_c:Q", title="気温(℃)", format=".2f"),
            ],
        )
        .add_params(year_selection)
        .properties(
            title="年別平均気温の推移",
            width="container",
            height=310,
        )
    )

    annual_chart_ui = mo.ui.altair_chart(annual_chart)

    year_count = int(filtered_annual["year"].n_unique())
    annual_mean = filtered_annual["annual_mean_temp_c"].mean()
    summer_mean = filtered_annual["summer_mean_temp_c"].mean()
    extreme_days = filtered_annual["extreme_hot_days"].mean()

    title = mo.md("# 東京の暑さの変化を追う")
    overview_header = mo.md(
        f"""
        対象期間 `{target_start}` 年から `{target_end}` 年までの `{year_count}` 年分を、年別推移、選択年の詳細、ランキング、期間比較で確認します。

        - 期間平均気温: `{annual_mean:.2f}℃`
        - 6-8月平均気温: `{summer_mean:.2f}℃`
        - 年間猛暑日数の平均: `{extreme_days:.1f}日`
        """
    )

    overview_panel = mo.vstack(
        [
            title,
            target_controls,
            overview_header,
            annual_chart_ui,
        ],
        gap=2,
    )
    overview_panel
    return (annual_chart_ui,)


@app.cell
def _(annual_chart_ui, filtered_annual):
    # クリックされた年があれば詳細ビューの対象年にする。未選択時は最新年を表示する。
    selected_year = int(filtered_annual["year"].max()) if not filtered_annual.is_empty() else None
    clicked = annual_chart_ui.value

    if clicked is not None and len(clicked) > 0:
        if hasattr(clicked, "row"):
            selected_year = int(clicked.row(0, named=True)["year"])
        elif isinstance(clicked, dict):
            selected_year = int(clicked["year"][0] if isinstance(clicked["year"], list) else clicked["year"])
        elif hasattr(clicked, "to_dicts"):
            selected_year = int(clicked.to_dicts()[0]["year"])
        elif hasattr(clicked, "to_dict"):
            selected_year = int(clicked.to_dict("records")[0]["year"])
        else:
            selected_year = int(clicked[0]["year"])
    return (selected_year,)


@app.cell
def _(
    SERIES_COLORS,
    alt,
    day_of_year_to_month_day,
    filtered_annual,
    filtered_daily,
    mo,
    pl,
    rank_position,
    selected_year,
    value_text,
):
    # 100年分の日別分布から、平年の「中央50%」にあたる帯を作る。
    daily_base = filtered_daily.filter(
        ~((pl.col("month") == 2) & (pl.col("day") == 29))
    )
    daily_band = (
        daily_base.group_by(["month", "day"])
        .agg(
            pl.col("avg_temp_c").quantile(0.25).alias("p25_temp_c"),
            pl.col("avg_temp_c").quantile(0.75).alias("p75_temp_c"),
            pl.col("avg_temp_c").mean().alias("normal_temp_c"),
        )
        .sort(["month", "day"])
        .with_columns(pl.date(pl.lit(2004), pl.col("month"), pl.col("day")).alias("plot_date"))
    )

    selected_daily = daily_base.filter(pl.col("year") == selected_year).with_columns(
        pl.date(pl.lit(2004), pl.col("month"), pl.col("day")).alias("plot_date")
    )

    band_area = (
        alt.Chart(daily_band)
        .mark_area(color="#c9d1d6", opacity=0.45)
        .encode(
            x=alt.X("plot_date:T", title="月日", axis=alt.Axis(format="%m/%d")),
            y=alt.Y("p25_temp_c:Q", title="平均気温(℃)"),
            y2="p75_temp_c:Q",
            tooltip=[
                alt.Tooltip("plot_date:T", title="月日", format="%m/%d"),
                alt.Tooltip("p25_temp_c:Q", title="25%点(℃)", format=".1f"),
                alt.Tooltip("p75_temp_c:Q", title="75%点(℃)", format=".1f"),
            ],
        )
    )

    normal_line = (
        alt.Chart(daily_band)
        .mark_line(color="#7b8790", strokeDash=[4, 4], size=1.5)
        .encode(
            x=alt.X("plot_date:T", title="月日", axis=alt.Axis(format="%m/%d")),
            y=alt.Y("normal_temp_c:Q", title="平均気温(℃)"),
        )
    )

    selected_line = (
        alt.Chart(selected_daily)
        .mark_line(color=SERIES_COLORS["6-8月平均気温"], size=3)
        .encode(
            x=alt.X("plot_date:T", title="月日", axis=alt.Axis(format="%m/%d")),
            y=alt.Y("avg_temp_c:Q", title="平均気温(℃)"),
            tooltip=[
                alt.Tooltip("observed_date:T", title="日付", format="%Y/%m/%d"),
                alt.Tooltip("avg_temp_c:Q", title="平均気温(℃)", format=".1f"),
                alt.Tooltip("max_temp_c:Q", title="最高気温(℃)", format=".1f"),
                alt.Tooltip("min_temp_c:Q", title="最低気温(℃)", format=".1f"),
            ],
        )
    )

    daily_chart = (
        (band_area + normal_line + selected_line)
        .resolve_scale(y="shared")
        .properties(
            title=f"{selected_year}年の日別平均気温と平年帯",
            width="container",
            height=300,
        )
    )
    daily_chart_ui = mo.ui.altair_chart(daily_chart)

    selected_row = filtered_annual.filter(pl.col("year") == selected_year).row(0, named=True)
    stat_cards = [
        {
            "label": "夏の始まり",
            "value": day_of_year_to_month_day(selected_row["first_summer_dayofyear"]),
            "caption": f"対象期間で {rank_position(filtered_annual, 'first_summer_dayofyear', selected_year, True)} の早さ",
            "color": SERIES_COLORS["夏日の初日"],
        },
        {
            "label": "夏の終わり",
            "value": day_of_year_to_month_day(selected_row["last_summer_dayofyear"]),
            "caption": f"対象期間で {rank_position(filtered_annual, 'last_summer_dayofyear', selected_year, False)} の遅さ",
            "color": "#596f8f",
        },
        {
            "label": "年間夏日日数",
            "value": value_text(selected_row["summer_days"], "日"),
            "caption": f"対象期間で {rank_position(filtered_annual, 'summer_days', selected_year, False)} の多さ",
            "color": SERIES_COLORS["夏日(最高25℃以上)"],
        },
        {
            "label": "年間猛暑日日数",
            "value": value_text(selected_row["extreme_hot_days"], "日"),
            "caption": f"対象期間で {rank_position(filtered_annual, 'extreme_hot_days', selected_year, False)} の多さ",
            "color": SERIES_COLORS["猛暑日(最高35℃以上)"],
        },
    ]

    year_detail_heading = mo.md(f"## {selected_year}年を掘る")
    year_detail_heading
    return daily_chart_ui, stat_cards


@app.cell
def _(daily_chart_ui):
    daily_chart_ui
    return


@app.cell
def _(stat_card_html, stat_cards):
    stat_card_html(stat_cards)
    return


@app.cell
def _(mo):
    ranking_category = mo.ui.radio(
        options=["夏日", "真夏日", "猛暑日", "熱帯夜"],
        value="夏日",
        inline=True,
        label="ランキングカテゴリ",
    )
    ranking_top_n = mo.ui.dropdown(
        options=["3", "5", "10"],
        value="5",
        label="上位件数",
    )

    ranking_controls = mo.hstack(
        [ranking_category, ranking_top_n],
        gap=2,
        justify="start",
    )
    return ranking_category, ranking_controls, ranking_top_n


@app.cell
def _(
    SERIES_COLORS,
    alt,
    day_of_year_to_month_day,
    filtered_annual,
    mo,
    pl,
    ranking_category,
    ranking_controls,
    ranking_top_n,
    value_text,
):
    category_specs = {
        "夏日": {
            "color": SERIES_COLORS["夏日(最高25℃以上)"],
            "count": "summer_days",
            "first": "first_summer_dayofyear",
            "last": "last_summer_dayofyear",
            "span": "summer_day_span",
        },
        "真夏日": {
            "color": SERIES_COLORS["真夏日(最高30℃以上)"],
            "count": "midsummer_days",
            "first": "first_midsummer_dayofyear",
            "last": "last_midsummer_dayofyear",
            "span": "midsummer_day_span",
        },
        "猛暑日": {
            "color": SERIES_COLORS["猛暑日(最高35℃以上)"],
            "count": "extreme_hot_days",
            "first": "first_extreme_hot_dayofyear",
            "last": "last_extreme_hot_dayofyear",
            "span": "extreme_hot_span",
        },
        "熱帯夜": {
            "color": SERIES_COLORS["熱帯夜(最低25℃以上)"],
            "count": "tropical_nights",
            "first": "first_tropical_night_dayofyear",
            "last": "last_tropical_night_dayofyear",
            "span": "tropical_night_span",
        },
    }
    category = ranking_category.value
    category_spec = category_specs[category]
    ranking_specs = [
        {
            "label": f"年間{category}数",
            "metric": category_spec["count"],
            "ascending": False,
            "value_kind": "count",
            "chart_group": "日数",
        },
        {
            "label": f"{category}の始まり",
            "metric": category_spec["first"],
            "ascending": True,
            "value_kind": "date",
            "chart_group": "時期",
        },
        {
            "label": f"{category}の終わり",
            "metric": category_spec["last"],
            "ascending": False,
            "value_kind": "date",
            "chart_group": "時期",
        },
        {
            "label": f"{category}の期間",
            "metric": category_spec["span"],
            "ascending": False,
            "value_kind": "count",
            "chart_group": "日数",
        },
    ]
    n = int(ranking_top_n.value)
    ranking_base = filtered_annual

    def top_rows(spec):
        return (
            ranking_base.drop_nulls([spec["metric"]])
            .sort(spec["metric"], descending=not spec["ascending"])
            .head(n)
            .select(["year", spec["metric"]])
        )

    def format_ranking_value(spec, value):
        if spec["value_kind"] == "date":
            return day_of_year_to_month_day(value)
        return value_text(value, "日")

    def ranking_card(spec):
        rows = []
        ranking = top_rows(spec)
        for index, row in enumerate(ranking.iter_rows(named=True)):
            raw_value = row[spec["metric"]]
            display_value = format_ranking_value(spec, raw_value)
            rows.append(
                f"""
                <div class="rank-list-row">
                  <span class="rank-list-number">{index + 1}</span>
                  <span class="rank-list-year">{int(row["year"])}年</span>
                  <strong>{display_value}</strong>
                </div>
                """
            )
        return f"""
        <section class="rank-list-card" style="--accent: {category_spec['color']};">
          <h3>{spec['label']}</h3>
          <div>{''.join(rows)}</div>
        </section>
        """

    ranking_cards = "\n".join(ranking_card(spec) for spec in ranking_specs)

    cards_html = mo.Html(
        f"""
        <style>
          .rank-list-board {{
            display: grid;
            gap: 12px;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          }}
          .rank-list-card {{
            background: #ffffff;
            border: 1px solid color-mix(in srgb, var(--accent) 24%, #dce4e2);
            border-top: 5px solid var(--accent);
            border-radius: 8px;
            box-shadow: 0 8px 20px rgba(22, 36, 45, 0.07);
            color: #1d2a30;
            padding: 13px 14px;
          }}
          .rank-list-card h3 {{
            font-size: 15px;
            margin: 0 0 9px;
          }}
          .rank-list-row {{
            align-items: center;
            border-top: 1px solid #edf1f0;
            display: grid;
            gap: 8px;
            grid-template-columns: 28px 1fr auto;
            min-height: 36px;
          }}
          .rank-list-row:first-child {{
            border-top: 0;
          }}
          .rank-list-number {{
            background: color-mix(in srgb, var(--accent) 16%, #f4faf8);
            border-radius: 999px;
            display: inline-grid;
            font-size: 12px;
            font-weight: 800;
            height: 24px;
            place-items: center;
            width: 24px;
          }}
          .rank-list-year {{
            font-size: 14px;
            font-weight: 700;
          }}
          .rank-list-row strong {{
            color: var(--accent);
            font-size: 16px;
          }}
        </style>
        <div class="rank-list-board">
          {ranking_cards}
        </div>
        """
    )

    trend_rows = []
    for spec in ranking_specs:
        ranked_years = set(top_rows(spec)["year"].to_list())
        trend_source = ranking_base.drop_nulls([spec["metric"]]).select(["year", spec["metric"]])
        for row in trend_source.iter_rows(named=True):
            trend_rows.append(
                {
                    "year": int(row["year"]),
                    "series": spec["label"],
                    "value": float(row[spec["metric"]]),
                    "month_day": day_of_year_to_month_day(row[spec["metric"]]),
                    "chart_group": spec["chart_group"],
                    "is_top_ranked": int(row["year"]) in ranked_years,
                }
            )

    trend = pl.DataFrame(trend_rows)
    day_trend = trend.filter(pl.col("chart_group") == "日数")
    timing_trend = trend.filter(pl.col("chart_group") == "時期")
    day_domain = [spec["label"] for spec in ranking_specs if spec["chart_group"] == "日数"]
    timing_domain = [spec["label"] for spec in ranking_specs if spec["chart_group"] == "時期"]
    day_range = [category_spec["color"], "#5c7896"]
    timing_range = [category_spec["color"], "#8f6a5a"]

    count_line = (
        alt.Chart(day_trend)
        .mark_line(opacity=0.78)
        .encode(
            x=alt.X("year:Q", title="年", axis=alt.Axis(format="d")),
            y=alt.Y("value:Q", title="日数"),
            color=alt.Color(
                "series:N",
                title="指標",
                scale=alt.Scale(domain=day_domain, range=day_range),
            ),
        )
    )
    count_points = (
        alt.Chart(day_trend)
        .mark_point(filled=True)
        .encode(
            x=alt.X("year:Q", title="年", axis=alt.Axis(format="d")),
            y=alt.Y("value:Q", title="日数"),
            color=alt.Color(
                "series:N",
                title="指標",
                scale=alt.Scale(domain=day_domain, range=day_range),
            ),
            opacity=alt.condition(alt.datum.is_top_ranked, alt.value(1.0), alt.value(0.18)),
            size=alt.condition(alt.datum.is_top_ranked, alt.value(95), alt.value(18)),
            tooltip=[
                alt.Tooltip("year:Q", title="年", format="d"),
                alt.Tooltip("series:N", title="指標"),
                alt.Tooltip("value:Q", title="日数", format=".0f"),
            ],
        )
    )
    count_chart = (
        (count_line + count_points)
        .properties(
            title=f"{category}の日数と期間の推移",
            width="container",
            height=300,
        )
    )
    count_chart_ui = mo.ui.altair_chart(count_chart)

    timing_line = (
        alt.Chart(timing_trend)
        .mark_line(opacity=0.78)
        .encode(
            x=alt.X("year:Q", title="年", axis=alt.Axis(format="d")),
            y=alt.Y("value:Q", title="通算日", scale=alt.Scale(zero=False, reverse=True)),
            color=alt.Color(
                "series:N",
                title="指標",
                scale=alt.Scale(domain=timing_domain, range=timing_range),
            ),
        )
    )
    timing_points = (
        alt.Chart(timing_trend)
        .mark_point(filled=True)
        .encode(
            x=alt.X("year:Q", title="年", axis=alt.Axis(format="d")),
            y=alt.Y("value:Q", title="通算日", scale=alt.Scale(zero=False, reverse=True)),
            color=alt.Color(
                "series:N",
                title="指標",
                scale=alt.Scale(domain=timing_domain, range=timing_range),
            ),
            opacity=alt.condition(alt.datum.is_top_ranked, alt.value(1.0), alt.value(0.18)),
            size=alt.condition(alt.datum.is_top_ranked, alt.value(95), alt.value(18)),
            tooltip=[
                alt.Tooltip("year:Q", title="年", format="d"),
                alt.Tooltip("series:N", title="指標"),
                alt.Tooltip("value:Q", title="通算日", format=".0f"),
                alt.Tooltip("month_day:N", title="月日"),
            ],
        )
    )
    timing_chart = (
        (timing_line + timing_points)
        .properties(
            title=f"{category}の始まりと終わり",
            width="container",
            height=300,
        )
    )
    timing_chart_ui = mo.ui.altair_chart(timing_chart)

    ranking_cards_panel = mo.vstack(
        [
            mo.md("## ランキングと100年推移"),
            ranking_controls,
            cards_html,
        ],
        gap=2,
    )
    ranking_cards_panel
    return count_chart_ui, timing_chart_ui


@app.cell
def _(count_chart_ui):
    count_chart_ui
    return


@app.cell
def _(timing_chart_ui):
    timing_chart_ui
    return


@app.cell
def _(end_year, mo, start_year, year_options):
    compare_left_start = mo.ui.dropdown(
        year_options,
        value="1971" if start_year <= 1971 <= end_year else str(start_year),
        label="比較A 開始年",
    )
    compare_right_start = mo.ui.dropdown(
        year_options,
        value=str(max(start_year, end_year - 9)),
        label="比較B 開始年",
    )
    return compare_left_start, compare_right_start


@app.cell
def _(compare_left_start, compare_right_start, end_year, mo, year_options):
    valid_left_end_options = [
        year for year in year_options if int(year) >= int(compare_left_start.value)
    ]
    valid_right_end_options = [
        year for year in year_options if int(year) >= int(compare_right_start.value)
    ]
    left_end_default = (
        "1980"
        if int(compare_left_start.value) <= 1980 <= end_year
        else str(min(int(compare_left_start.value) + 9, end_year))
    )
    compare_left_end = mo.ui.dropdown(
        valid_left_end_options,
        value=left_end_default,
        label="比較A 終了年",
    )
    compare_right_end = mo.ui.dropdown(
        valid_right_end_options,
        value=str(end_year),
        label="比較B 終了年",
    )

    compare_controls = mo.hstack(
        [
            compare_left_start,
            compare_left_end,
            compare_right_start,
            compare_right_end,
        ],
        gap=2,
        justify="start",
    )
    return compare_controls, compare_left_end, compare_right_end


@app.cell
def _(
    annual,
    build_metric_table,
    build_timing_table,
    compare_controls,
    compare_left_end,
    compare_left_start,
    compare_right_end,
    compare_right_start,
    day_of_year_to_month_day,
    difference,
    format_float,
    mo,
    period_slice,
    stat_card_html,
):
    # 比較A/Bは、このビューの中でだけ使うローカルな分析条件にする。
    left_years = (int(compare_left_start.value), int(compare_left_end.value))
    right_years = (int(compare_right_start.value), int(compare_right_end.value))
    left_label = f"{min(left_years)}-{max(left_years)}"
    right_label = f"{min(right_years)}-{max(right_years)}"

    left_annual = period_slice(annual, *left_years)
    right_annual = period_slice(annual, *right_years)

    annual_temp_diff = right_annual["annual_mean_temp_c"].mean() - left_annual["annual_mean_temp_c"].mean()
    summer_temp_diff = right_annual["summer_mean_temp_c"].mean() - left_annual["summer_mean_temp_c"].mean()
    summer_days_diff = right_annual["summer_days"].mean() - left_annual["summer_days"].mean()
    extreme_days_diff = right_annual["extreme_hot_days"].mean() - left_annual["extreme_hot_days"].mean()
    summer_span_diff = right_annual["summer_day_span"].median() - left_annual["summer_day_span"].median()
    first_summer_diff = right_annual["first_summer_dayofyear"].median() - left_annual["first_summer_dayofyear"].median()

    impact_cards = [
        {
            "label": "年平均気温",
            "value": f"{annual_temp_diff:+.2f}℃",
            "caption": f"{left_label} から {right_label} への差",
            "color": "#31688e",
        },
        {
            "label": "6-8月平均気温",
            "value": f"{summer_temp_diff:+.2f}℃",
            "caption": "夏の平均的な底上げ",
            "color": "#e07b39",
        },
        {
            "label": "猛暑日数/年",
            "value": f"{extreme_days_diff:+.1f}日",
            "caption": "年間平均の差",
            "color": "#8c564b",
        },
        {
            "label": "夏日期間",
            "value": f"{summer_span_diff:+.0f}日",
            "caption": "中央値の差",
            "color": "#2ca02c",
        },
        {
            "label": "夏日の初日",
            "value": f"{first_summer_diff:+.0f}日",
            "caption": "マイナスなら前倒し",
            "color": "#5d7191",
        },
    ]

    overall_compare = build_metric_table(
        [
            (
                "年平均気温(℃)",
                format_float(left_annual["annual_mean_temp_c"].mean(), 2),
                format_float(right_annual["annual_mean_temp_c"].mean(), 2),
                difference(left_annual["annual_mean_temp_c"].mean(), right_annual["annual_mean_temp_c"].mean(), 2),
            ),
            (
                "6-8月平均気温(℃)",
                format_float(left_annual["summer_mean_temp_c"].mean(), 2),
                format_float(right_annual["summer_mean_temp_c"].mean(), 2),
                difference(left_annual["summer_mean_temp_c"].mean(), right_annual["summer_mean_temp_c"].mean(), 2),
            ),
            (
                "夏日数/年",
                format_float(left_annual["summer_days"].mean(), 1),
                format_float(right_annual["summer_days"].mean(), 1),
                difference(left_annual["summer_days"].mean(), right_annual["summer_days"].mean(), 1),
            ),
            (
                "真夏日数/年",
                format_float(left_annual["midsummer_days"].mean(), 1),
                format_float(right_annual["midsummer_days"].mean(), 1),
                difference(left_annual["midsummer_days"].mean(), right_annual["midsummer_days"].mean(), 1),
            ),
            (
                "猛暑日数/年",
                format_float(left_annual["extreme_hot_days"].mean(), 1),
                format_float(right_annual["extreme_hot_days"].mean(), 1),
                difference(left_annual["extreme_hot_days"].mean(), right_annual["extreme_hot_days"].mean(), 1),
            ),
        ],
        left_label,
        right_label,
    )

    timing_compare = build_timing_table(
        [
            (
                "夏日の初日",
                format_float(left_annual["first_summer_dayofyear"].median(), 0),
                day_of_year_to_month_day(left_annual["first_summer_dayofyear"].median()),
                format_float(right_annual["first_summer_dayofyear"].median(), 0),
                day_of_year_to_month_day(right_annual["first_summer_dayofyear"].median()),
                difference(left_annual["first_summer_dayofyear"].median(), right_annual["first_summer_dayofyear"].median(), 0),
            ),
            (
                "真夏日の初日",
                format_float(left_annual["first_midsummer_dayofyear"].median(), 0),
                day_of_year_to_month_day(left_annual["first_midsummer_dayofyear"].median()),
                format_float(right_annual["first_midsummer_dayofyear"].median(), 0),
                day_of_year_to_month_day(right_annual["first_midsummer_dayofyear"].median()),
                difference(left_annual["first_midsummer_dayofyear"].median(), right_annual["first_midsummer_dayofyear"].median(), 0),
            ),
            (
                "夏日期間(日)",
                format_float(left_annual["summer_day_span"].median(), 0),
                "-",
                format_float(right_annual["summer_day_span"].median(), 0),
                "-",
                difference(left_annual["summer_day_span"].median(), right_annual["summer_day_span"].median(), 0),
            ),
        ],
        left_label,
        right_label,
    )

    compare_panel = mo.vstack(
        [
            mo.md("## 期間比較"),
            compare_controls,
            stat_card_html(impact_cards),
            mo.md("### 全体の底上げ"),
            mo.ui.table(overall_compare),
            mo.md("### 夏の前倒しと長期化"),
            mo.ui.table(timing_compare),
        ],
        gap=2,
    )
    compare_panel
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
