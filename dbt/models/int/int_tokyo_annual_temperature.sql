with daily as (
    select
        year,
        month,
        avg_temp_c,
        max_temp_c,
        min_temp_c,
        is_summer_day,
        is_midsummer_day,
        is_extreme_hot_day,
        is_kokusho_day,
        is_tropical_night
    from {{ ref('int_tokyo_daily_temperature_features') }}
)

select
    year,
    count(*)::int as observed_days,
    avg(avg_temp_c) as annual_mean_temp_c,
    avg(case when month between 6 and 8 then avg_temp_c end) as summer_mean_temp_c,
    avg(case when month between 1 and 12 then max_temp_c end) as annual_mean_max_temp_c,
    avg(case when month between 1 and 12 then min_temp_c end) as annual_mean_min_temp_c,
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
order by 1
