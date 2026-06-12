with daily as (
    select
        year,
        observed_date,
        dayofyear,
        month,
        is_summer_day,
        is_midsummer_day,
        is_tropical_night,
        is_5dayavg30_or_higher
    from {{ ref('int_tokyo_daily_temperature_features') }}
),
yearly as (
    select distinct year
    from daily
),
events as (
    select
        year,
        min(case when is_summer_day then observed_date end) as first_summer_date,
        min(case when is_midsummer_day then observed_date end) as first_midsummer_date,
        min(case when is_5dayavg30_or_higher then observed_date end) as first_5dayavg30_date,
        min(case when is_tropical_night then observed_date end) as first_tropical_night_date,
        max(case when is_summer_day then observed_date end) as last_summer_date,
        max(case when is_midsummer_day then observed_date end) as last_midsummer_date
    from daily
    group by 1
)

select
    y.year,
    e.first_summer_date,
    extract(doy from e.first_summer_date)::int as first_summer_dayofyear,
    e.first_midsummer_date,
    extract(doy from e.first_midsummer_date)::int as first_midsummer_dayofyear,
    e.first_5dayavg30_date,
    extract(doy from e.first_5dayavg30_date)::int as first_5dayavg30_dayofyear,
    e.first_tropical_night_date,
    extract(doy from e.first_tropical_night_date)::int as first_tropical_night_dayofyear,
    e.last_summer_date,
    extract(doy from e.last_summer_date)::int as last_summer_dayofyear,
    e.last_midsummer_date,
    extract(doy from e.last_midsummer_date)::int as last_midsummer_dayofyear,
    (extract(doy from e.last_summer_date)::int - extract(doy from e.first_summer_date)::int + 1) as summer_day_span,
    (extract(doy from e.last_midsummer_date)::int - extract(doy from e.first_midsummer_date)::int + 1) as midsummer_day_span
from yearly as y
left join events as e
    on y.year = e.year
order by y.year
