{{ config(materialized='table') }}

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2000-01-01' as date)",
        end_date="cast('2035-12-31' as date)"
    ) }}
)

select
    cast(date_day as date) as date,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    extract(day from date_day) as day,
{% if target.type == 'bigquery' %}
    extract(dayofweek from date_day) as day_of_week,
    format_date('%A', date_day) as day_name,
    extract(isoweek from date_day) as week_of_year,
    date_day = last_day(date_day, month) as is_month_end,
    date_day = last_day(date_day, quarter) as is_quarter_end,
    date_day = last_day(date_day, year) as is_year_end
{% else %}
    (extract(dow from date_day) + 1) as day_of_week,
    strftime(date_day, '%A') as day_name,
    extract(week from date_day) as week_of_year,
    date_day = (date_trunc('month', date_day) + interval '1 month' - interval '1 day') as is_month_end,
    date_day = (date_trunc('quarter', date_day) + interval '3 month' - interval '1 day') as is_quarter_end,
    date_day = (date_trunc('year', date_day) + interval '1 year' - interval '1 day') as is_year_end
{% endif %}
from date_spine
