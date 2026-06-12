with daily as (
    select
        observed_date,
        year,
        month,
        day,
        dayofyear,
        month_label,
        avg_temp_c,
        max_temp_c,
        min_temp_c,
        is_summer_day,
        is_midsummer_day,
        is_extreme_hot_day,
        is_kokusho_day,
        is_tropical_night,
        source_file
    from {{ ref('stg_jma_tokyo_daily_temperature') }}
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
)

select
    observed_date,
    year,
    month,
    day,
    dayofyear,
    month_label,
    avg_temp_c,
    max_temp_c,
    min_temp_c,
    is_summer_day,
    is_midsummer_day,
    is_extreme_hot_day,
    is_kokusho_day,
    is_tropical_night,
    rolling_5day_max_temp_c,
    (rolling_5day_count = 5 and rolling_5day_max_temp_c >= 30) as is_5dayavg30_or_higher,
    source_file
from rolling
