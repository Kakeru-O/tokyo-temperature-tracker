with source as (
    select
        *
    from read_csv_auto(
        '{{ var("processed_jma_tokyo_glob") }}',
        header=true,
        union_by_name=true
    )
)

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
    (max_temp_c >= 25) as is_summer_day,
    (max_temp_c >= 30) as is_midsummer_day,
    (max_temp_c >= 35) as is_extreme_hot_day,
    (max_temp_c >= 40) as is_kokusho_day,
    (min_temp_c >= 25) as is_tropical_night,
    source_file
from source
