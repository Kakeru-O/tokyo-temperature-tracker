with monthly as (
    select
        month_start,
        year,
        month,
        observed_days,
        mean_avg_temp_c,
        mean_max_temp_c,
        mean_min_temp_c,
        abs_max_temp_c,
        abs_min_temp_c
    from {{ ref('int_tokyo_monthly_temperature') }}
),
baseline as (
    select
        month,
        avg(mean_avg_temp_c) as baseline_mean_avg_temp_c_1991_2020,
        avg(mean_max_temp_c) as baseline_mean_max_temp_c_1991_2020,
        avg(mean_min_temp_c) as baseline_mean_min_temp_c_1991_2020
    from monthly
    where year between 1991 and 2020
    group by 1
)

select
    m.month_start,
    m.year,
    m.month,
    m.observed_days,
    m.mean_avg_temp_c,
    m.mean_max_temp_c,
    m.mean_min_temp_c,
    m.abs_max_temp_c,
    m.abs_min_temp_c,
    b.baseline_mean_avg_temp_c_1991_2020,
    b.baseline_mean_max_temp_c_1991_2020,
    b.baseline_mean_min_temp_c_1991_2020,
    (m.mean_avg_temp_c - b.baseline_mean_avg_temp_c_1991_2020) as anomaly_mean_avg_temp_c_1991_2020,
    (m.mean_max_temp_c - b.baseline_mean_max_temp_c_1991_2020) as anomaly_mean_max_temp_c_1991_2020,
    (m.mean_min_temp_c - b.baseline_mean_min_temp_c_1991_2020) as anomaly_mean_min_temp_c_1991_2020
from monthly as m
left join baseline as b
    on m.month = b.month

