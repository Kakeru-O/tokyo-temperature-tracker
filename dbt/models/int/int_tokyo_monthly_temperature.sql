with daily as (
    select
        observed_date,
        avg_temp_c,
        max_temp_c,
        min_temp_c
    from {{ ref('stg_jma_tokyo_daily_temperature') }}
),
monthly as (
    select
        date_trunc('month', observed_date)::date as month_start,
        extract(year from observed_date)::int as year,
        extract(month from observed_date)::int as month,
        count(*)::int as observed_days,
        avg(avg_temp_c) as mean_avg_temp_c,
        avg(max_temp_c) as mean_max_temp_c,
        avg(min_temp_c) as mean_min_temp_c,
        max(max_temp_c) as abs_max_temp_c,
        min(min_temp_c) as abs_min_temp_c
    from daily
    group by 1, 2, 3
)

select *
from monthly

