#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import duckdb


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    db_path = root / "tokyo_temperature.duckdb"
    out_dir = root / "data" / "pages"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        raise SystemExit(
            f"{db_path} が見つかりません。先に `uv run dbt build --project-dir dbt --profiles-dir dbt` を実行してください。"
        )

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        con.execute(
            f"""
            copy (
                select *
                from mart.mart_tokyo_temperature_story_metrics
                order by year
            )
            to '{out_dir / "annual_metrics.csv"}'
            with (header, delimiter ',')
            """
        )
        con.execute(
            f"""
            copy (
                select
                    observed_date,
                    year,
                    month,
                    day,
                    dayofyear,
                    avg_temp_c,
                    max_temp_c,
                    min_temp_c,
                    is_summer_day,
                    is_midsummer_day,
                    is_extreme_hot_day,
                    is_tropical_night
                from int.int_tokyo_daily_temperature_features
                order by observed_date
            )
            to '{out_dir / "daily_features.csv"}'
            with (header, delimiter ',')
            """
        )
    finally:
        con.close()

    print(f"wrote {out_dir.relative_to(root)}")


if __name__ == "__main__":
    main()
