#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import polars as pl


RAW_COLUMNS = [
    "date",
    "avg_temp_c",
    "avg_quality",
    "avg_homogenization",
    "max_temp_c",
    "max_quality",
    "max_homogenization",
    "min_temp_c",
    "min_quality",
    "min_homogenization",
]


def load_raw_csv(path: Path) -> pl.DataFrame:
    numeric_cols = [column for column in RAW_COLUMNS if column != "date"]
    return (
        pl.read_csv(
            path,
            skip_rows=6,
            has_header=False,
            new_columns=RAW_COLUMNS,
            encoding="shift_jis",
        )
        .with_columns(
            pl.col("date").str.strptime(pl.Date, "%Y/%m/%d"),
            *[pl.col(column).cast(pl.Float64, strict=False) for column in numeric_cols],
            pl.lit(path.name).alias("source_file"),
        )
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(raw_dir.glob("jma_tokyo_*.csv"))
    if not raw_files:
        raise SystemExit(f"raw files not found: {raw_dir}")

    for raw_path in raw_files:
        df = load_raw_csv(raw_path)
        out_path = processed_dir / raw_path.name
        df.write_csv(out_path)
        print(f"wrote {out_path.relative_to(root)}")


if __name__ == "__main__":
    main()
