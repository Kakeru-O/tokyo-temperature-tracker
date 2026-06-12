with annual as (
    select
        year,
        observed_days,
        annual_mean_temp_c,
        summer_mean_temp_c,
        annual_mean_max_temp_c,
        annual_mean_min_temp_c,
        annual_max_temp_c,
        annual_min_temp_c,
        summer_days,
        midsummer_days,
        extreme_hot_days,
        kokusho_days,
        tropical_nights,
        may_summer_days,
        october_summer_days
    from {{ ref('int_tokyo_annual_temperature') }}
),
timing as (
    select
        year,
        first_summer_date,
        first_summer_dayofyear,
        first_midsummer_date,
        first_midsummer_dayofyear,
        first_5dayavg30_date,
        first_5dayavg30_dayofyear,
        first_tropical_night_date,
        first_tropical_night_dayofyear,
        last_summer_date,
        last_summer_dayofyear,
        last_midsummer_date,
        last_midsummer_dayofyear,
        summer_day_span,
        midsummer_day_span
    from {{ ref('int_tokyo_summer_timing') }}
),
streaks as (
    select
        year,
        longest_tropical_night_streak_start_date,
        longest_tropical_night_streak_end_date,
        longest_tropical_night_streak_start_dayofyear,
        longest_tropical_night_streak_end_dayofyear,
        longest_tropical_night_streak_value
    from {{ ref('int_tokyo_tropical_night_streaks') }}
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
    t.first_summer_date,
    t.first_summer_dayofyear,
    t.first_midsummer_date,
    t.first_midsummer_dayofyear,
    t.first_5dayavg30_date,
    t.first_5dayavg30_dayofyear,
    t.first_tropical_night_date,
    t.first_tropical_night_dayofyear,
    t.last_summer_date,
    t.last_summer_dayofyear,
    t.last_midsummer_date,
    t.last_midsummer_dayofyear,
    t.summer_day_span,
    t.midsummer_day_span,
    s.longest_tropical_night_streak_start_date,
    s.longest_tropical_night_streak_end_date,
    s.longest_tropical_night_streak_start_dayofyear,
    s.longest_tropical_night_streak_end_dayofyear,
    s.longest_tropical_night_streak_value
from annual as a
left join timing as t
    on a.year = t.year
left join streaks as s
    on a.year = s.year
order by a.year
