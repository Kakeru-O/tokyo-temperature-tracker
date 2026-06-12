from __future__ import annotations

from datetime import date, timedelta
from math import isnan
from pathlib import Path

import duckdb
import polars as pl

SERIES_COLORS = {
    "年平均気温": "#1f77b4",
    "6-8月平均気温": "#ff7f0e",
    "夏日(最高25℃以上)": "#2ca02c",
    "真夏日(最高30℃以上)": "#d62728",
    "猛暑日(最高35℃以上)": "#8c564b",
    "熱帯夜(最低25℃以上)": "#9467bd",
    "5日平均で30℃超": "#e377c2",
    "夏日の初日": "#2ca02c",
    "真夏日の初日": "#d62728",
    "熱帯夜の初日": "#9467bd",
    "夏日の最終日": "#2ca02c",
    "真夏日の最終日": "#d62728",
    "夏日の期間": "#2ca02c",
    "真夏日の期間": "#d62728",
    "5月の夏日数": "#2ca02c",
    "10月の夏日数": "#d62728",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def duckdb_path(root: Path | None = None) -> Path:
    base = root or project_root()
    return base / "tokyo_temperature.duckdb"


def processed_glob(root: Path | None = None) -> str:
    base = root or project_root()
    return str(base / "data" / "processed" / "jma_tokyo_*.csv")


def query_polars(con: duckdb.DuckDBPyConnection, sql: str) -> pl.DataFrame:
    result = con.execute(sql)
    columns = [column[0] for column in result.description]
    return pl.DataFrame(result.fetchall(), schema=columns, orient="row")


def load_metrics(root: Path | None = None) -> pl.DataFrame:
    base = root or project_root()
    db_path = duckdb_path(base)
    if db_path.exists():
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            has_table = con.execute(
                """
                select 1
                from information_schema.tables
                where table_schema = 'mart'
                  and table_name = 'mart_tokyo_temperature_story_metrics'
                limit 1
                """
            ).fetchone()
            if has_table:
                return query_polars(
                    con,
                    """
                    select *
                    from mart.mart_tokyo_temperature_story_metrics
                    order by year
                    """,
                )
        finally:
            con.close()
    return build_metrics_from_processed(base)


def load_daily_data(root: Path | None = None) -> pl.DataFrame:
    base = root or project_root()
    db_path = duckdb_path(base)
    if db_path.exists():
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            has_table = con.execute(
                """
                select 1
                from information_schema.tables
                where table_schema = 'intermediate'
                  and table_name = 'int_tokyo_daily_temperature_features'
                limit 1
                """
            ).fetchone()
            if has_table:
                return query_polars(
                    con,
                    """
                    select *
                    from intermediate.int_tokyo_daily_temperature_features
                    order by observed_date
                    """,
                )
        finally:
            con.close()
    
    # Fallback to CSV
    source_glob = processed_glob(base)
    con = duckdb.connect()
    try:
        return query_polars(
            con,
            f"""
            select
                date::date as observed_date,
                extract(year from date)::int as year,
                extract(month from date)::int as month,
                extract(day from date)::int as day,
                extract(doy from date)::int as dayofyear,
                avg_temp_c,
                max_temp_c,
                min_temp_c,
                (max_temp_c >= 25) as is_summer_day,
                (max_temp_c >= 30) as is_midsummer_day,
                (max_temp_c >= 35) as is_extreme_hot_day,
                (min_temp_c >= 25) as is_tropical_night
            from read_csv_auto(
                '{source_glob}',
                header=true,
                union_by_name=true
            )
            order by observed_date
            """,
        )
    finally:
        con.close()



def build_metrics_from_processed(root: Path | None = None) -> pl.DataFrame:
    base = root or project_root()
    source_glob = processed_glob(base)
    con = duckdb.connect()
    try:
        return query_polars(
            con,
            f"""
            with daily as (
                select
                    date::date as observed_date,
                    extract(year from date)::int as year,
                    extract(month from date)::int as month,
                    extract(day from date)::int as day,
                    extract(doy from date)::int as dayofyear,
                    strftime(date, '%Y-%m') as month_label,
                    avg_temp_c,
                    max_temp_c,
                    min_temp_c,
                    avg_quality,
                    max_quality,
                    min_quality,
                    avg_homogenization,
                    max_homogenization,
                    min_homogenization,
                    source_file,
                    (max_temp_c >= 25) as is_summer_day,
                    (max_temp_c >= 30) as is_midsummer_day,
                    (max_temp_c >= 35) as is_extreme_hot_day,
                    (max_temp_c >= 40) as is_kokusho_day,
                    (min_temp_c >= 25) as is_tropical_night
                from read_csv_auto(
                    '{source_glob}',
                    header=true,
                    union_by_name=true
                )
            ),
            rolling as (
                select
                    daily.*,
                    avg(max_temp_c) over (
                        partition by year
                        order by observed_date
                        rows between 4 preceding and current row
                    ) as rolling_5day_max_temp_c,
                    count(*) over (
                        partition by year
                        order by observed_date
                        rows between 4 preceding and current row
                    ) as rolling_5day_count
                from daily
            ),
            annual as (
                select
                    year,
                    count(*)::int as observed_days,
                    avg(avg_temp_c) as annual_mean_temp_c,
                    avg(case when month between 6 and 8 then avg_temp_c end) as summer_mean_temp_c,
                    avg(max_temp_c) as annual_mean_max_temp_c,
                    avg(min_temp_c) as annual_mean_min_temp_c,
                    max(max_temp_c) as annual_max_temp_c,
                    min(min_temp_c) as annual_min_temp_c,
                    sum(case when is_summer_day then 1 else 0 end)::int as summer_days,
                    sum(case when is_midsummer_day then 1 else 0 end)::int as midsummer_days,
                    sum(case when is_extreme_hot_day then 1 else 0 end)::int as extreme_hot_days,
                    sum(case when is_kokusho_day then 1 else 0 end)::int as kokusho_days,
                    sum(case when is_tropical_night then 1 else 0 end)::int as tropical_nights,
                    sum(case when month = 5 and is_summer_day then 1 else 0 end)::int as may_summer_days,
                    sum(case when month = 10 and is_summer_day then 1 else 0 end)::int as october_summer_days
                from daily
                group by 1
            ),
            start_events as (
                select
                    year,
                    min(case when is_summer_day then observed_date end) as first_summer_date,
                    min(case when is_midsummer_day then observed_date end) as first_midsummer_date,
                    min(case when rolling_5day_count = 5 and rolling_5day_max_temp_c >= 30 then observed_date end) as first_5dayavg30_date,
                    min(case when is_tropical_night then observed_date end) as first_tropical_night_date
                from rolling
                group by 1
            ),
            end_events as (
                select
                    year,
                    max(case when is_summer_day then observed_date end) as last_summer_date,
                    max(case when is_midsummer_day then observed_date end) as last_midsummer_date
                from daily
                group by 1
            ),
            night_runs as (
                select
                    year,
                    observed_date,
                    extract(doy from observed_date)::int as dayofyear,
                    observed_date - row_number() over (
                        partition by year
                        order by observed_date
                    )::int as run_key
                from daily
                where is_tropical_night
            ),
            night_streaks as (
                select
                    year,
                    run_key,
                    min(observed_date) as streak_start_date,
                    max(observed_date) as streak_end_date,
                    min(dayofyear) as streak_start_dayofyear,
                    max(dayofyear) as streak_end_dayofyear,
                    count(*)::int as streak_length
                from night_runs
                group by 1, 2
            ),
            ranked_night_streaks as (
                select
                    *,
                    row_number() over (
                        partition by year
                        order by streak_length desc, streak_start_date asc
                    ) as rn
                from night_streaks
            )
            select
                a.year,
                a.observed_days,
                a.annual_mean_temp_c,
                a.summer_mean_temp_c,
                a.annual_mean_max_temp_c,
                a.annual_mean_min_temp_c,
                a.annual_max_temp_c,
                a.annual_min_temp_c,
                a.summer_days,
                a.midsummer_days,
                a.extreme_hot_days,
                a.kokusho_days,
                a.tropical_nights,
                a.may_summer_days,
                a.october_summer_days,
                s.first_summer_date,
                extract(doy from s.first_summer_date)::int as first_summer_dayofyear,
                s.first_midsummer_date,
                extract(doy from s.first_midsummer_date)::int as first_midsummer_dayofyear,
                s.first_5dayavg30_date,
                extract(doy from s.first_5dayavg30_date)::int as first_5dayavg30_dayofyear,
                s.first_tropical_night_date,
                extract(doy from s.first_tropical_night_date)::int as first_tropical_night_dayofyear,
                e.last_summer_date,
                extract(doy from e.last_summer_date)::int as last_summer_dayofyear,
                e.last_midsummer_date,
                extract(doy from e.last_midsummer_date)::int as last_midsummer_dayofyear,
                date_diff('day', s.first_summer_date, e.last_summer_date) + 1 as summer_day_span,
                date_diff('day', s.first_midsummer_date, e.last_midsummer_date) + 1 as midsummer_day_span,
                r.streak_start_date as longest_tropical_night_streak_start_date,
                r.streak_end_date as longest_tropical_night_streak_end_date,
                r.streak_start_dayofyear as longest_tropical_night_streak_start_dayofyear,
                r.streak_end_dayofyear as longest_tropical_night_streak_end_dayofyear,
                r.streak_length as longest_tropical_night_streak_value
            from annual as a
            left join start_events as s
                on a.year = s.year
            left join end_events as e
                on a.year = e.year
            left join ranked_night_streaks as r
                on a.year = r.year
               and r.rn = 1
            order by a.year
            """,
        )
    finally:
        con.close()


def period_slice(df: pl.DataFrame, y0: int, y1: int) -> pl.DataFrame:
    start_year = min(y0, y1)
    end_year = max(y0, y1)
    return df.filter(pl.col("year").is_between(start_year, end_year))


def format_float(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def difference(left: float, right: float, digits: int) -> str:
    return f"{right - left:+.{digits}f}"


def day_of_year_to_month_day(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and isnan(value):
        return "-"
    dayofyear = int(round(float(value)))
    target_date = date(2004, 1, 1) + timedelta(days=dayofyear - 1)
    return target_date.strftime("%m/%d")


def build_metric_table(rows: list[tuple[str, str, str, str]], left_label: str, right_label: str) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=["指標", left_label, right_label, "差分(後-前)"], orient="row")


def build_timing_table(
    rows: list[tuple[str, str, str, str, str, str]],
    left_label: str,
    right_label: str,
) -> pl.DataFrame:
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


def rank_rows(df: pl.DataFrame, metric: str, ascending: bool, top_n: int, columns: list[str]) -> pl.DataFrame:
    return (
        df.sort(metric, descending=not ascending)
        .select(columns)
        .head(top_n)
    )
