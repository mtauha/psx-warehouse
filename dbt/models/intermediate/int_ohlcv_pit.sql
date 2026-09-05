{{
    config(
        materialized='incremental',
        unique_key=['ticker_key', 'date'],
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns'
    )
}}

with first_observed as (

    select
        symbol,
        date,
        open,
        high,
        low,
        close,
        volume,
        is_anomaly,
        row_number() over (
            partition by symbol, date order by loaded_at asc
        ) as rn
    from {{ ref('stg_stock_history') }}
    {% if is_incremental() %}
    -- Same buffer sizing as int_technical_indicators: PSX trades ~250 days/year, so
    -- 750 calendar days comfortably covers the 199-row rolling_vol_200 lookback (and
    -- the smaller 63-row trailing_return_63d lookback) at the oldest written row.
    and date >= cast({{ dbt.dateadd('day', -750, 'current_date') }} as date)
    {% endif %}

),

base as (

    select symbol, date, open, high, low, close, volume, is_anomaly
    from first_observed
    where rn = 1

),

returns as (

    select
        symbol,
        date,
        open,
        high,
        low,
        close,
        volume,
        is_anomaly,
        (close - lag(close) over (partition by symbol order by date))
            / lag(close) over (partition by symbol order by date) as daily_return_pct
    from base

),

derived as (

    select
        symbol,
        date,
        open,
        high,
        low,
        close,
        volume,
        is_anomaly,
        daily_return_pct,
        stddev(daily_return_pct) over (
            partition by symbol order by date rows between 199 preceding and current row
        ) as rolling_vol_200,
        (close - lag(close, 63) over (partition by symbol order by date))
            / lag(close, 63) over (partition by symbol order by date) as trailing_return_63d
    from returns

)

select
    coalesce(real_match.dbt_scd_id, earliest_match.dbt_scd_id) as ticker_key,
    d.symbol,
    d.date,
    d.open,
    d.high,
    d.low,
    d.close,
    d.volume,
    d.is_anomaly,
    d.daily_return_pct,
    d.rolling_vol_200,
    d.trailing_return_63d
from derived d
{{ as_of_ticker_join('d', 'date') }}
{% if is_incremental() %}
where d.date >= cast({{ dbt.dateadd('day', -250, 'current_date') }} as date)
{% endif %}
