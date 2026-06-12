with daily as (
    select
        year,
        observed_date,
        dayofyear,
        is_tropical_night
    from {{ ref('int_tokyo_daily_temperature_features') }}
),
runs as (
    select
        year,
        observed_date,
        dayofyear,
        observed_date - row_number() over (
            partition by year
            order by observed_date
        )::int as run_key
    from daily
    where is_tropical_night
),
streaks as (
    select
        year,
        run_key,
        min(observed_date) as streak_start_date,
        max(observed_date) as streak_end_date,
        min(dayofyear) as streak_start_dayofyear,
        max(dayofyear) as streak_end_dayofyear,
        count(*)::int as streak_length
    from runs
    group by 1, 2
),
ranked as (
    select
        *,
        row_number() over (
            partition by year
            order by streak_length desc, streak_start_date asc
        ) as rn
    from streaks
)

select
    year,
    streak_start_date as longest_tropical_night_streak_start_date,
    streak_end_date as longest_tropical_night_streak_end_date,
    streak_start_dayofyear as longest_tropical_night_streak_start_dayofyear,
    streak_end_dayofyear as longest_tropical_night_streak_end_dayofyear,
    streak_length as longest_tropical_night_streak_value
from ranked
where rn = 1
order by year
