{{
    config(
        materialized='incremental',
        unique_key=['symbol', 'date'],
        incremental_strategy='delete+insert'
    )
}}

with base as (

    select
        symbol,
        date,
        close
    from {{ ref('stg_stock_history') }}
    where is_latest = true
    {% if is_incremental() %}
    and date >= {{ dbt.dateadd('day', -500, 'current_date') }}
    {% endif %}

),

returns as (

    select
        symbol,
        date,
        close,
        (close - lag(close) over (partition by symbol order by date))
            / lag(close) over (partition by symbol order by date) as daily_return_pct
    from base

),

moving_averages as (

    select
        symbol,
        date,
        close,
        daily_return_pct,
        avg(close) over (
            partition by symbol order by date rows between 19 preceding and current row
        ) as ma_20,
        avg(close) over (
            partition by symbol order by date rows between 49 preceding and current row
        ) as ma_50,
        avg(close) over (
            partition by symbol order by date rows between 199 preceding and current row
        ) as ma_200,
        stddev(daily_return_pct) over (
            partition by symbol order by date rows between 19 preceding and current row
        ) as rolling_vol_20,
        stddev(daily_return_pct) over (
            partition by symbol order by date rows between 49 preceding and current row
        ) as rolling_vol_50,
        stddev(daily_return_pct) over (
            partition by symbol order by date rows between 199 preceding and current row
        ) as rolling_vol_200,
        (close - lag(close, 5) over (partition by symbol order by date))
            / lag(close, 5) over (partition by symbol order by date) as trailing_return_5d,
        (close - lag(close, 252) over (partition by symbol order by date))
            / lag(close, 252) over (partition by symbol order by date) as trailing_return_252d
    from returns

),

gain_loss as (

    select
        symbol,
        date,
        greatest(close - lag(close) over (partition by symbol order by date), 0) as gain,
        greatest(lag(close) over (partition by symbol order by date) - close, 0) as loss
    from base

),

rsi as (

    select
        symbol,
        date,
        avg(gain) over (
            partition by symbol order by date rows between 13 preceding and current row
        ) as avg_gain_14,
        avg(loss) over (
            partition by symbol order by date rows between 13 preceding and current row
        ) as avg_loss_14
    from gain_loss

),

final as (

    select
        m.symbol,
        m.date,
        m.daily_return_pct,
        m.ma_20,
        m.ma_50,
        m.ma_200,
        case
            when r.avg_loss_14 = 0 and r.avg_gain_14 = 0 then null
            when r.avg_loss_14 = 0 then 100
            else 100 - (100 / (1 + (r.avg_gain_14 / r.avg_loss_14)))
        end as rsi_14,
        m.rolling_vol_20,
        m.rolling_vol_50,
        m.rolling_vol_200,
        m.trailing_return_5d,
        m.trailing_return_252d
    from moving_averages m
    inner join rsi r on m.symbol = r.symbol and m.date = r.date

)

select *
from final
{% if is_incremental() %}
where date >= {{ dbt.dateadd('day', -250, 'current_date') }}
{% endif %}
