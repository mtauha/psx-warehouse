{{
    config(
        materialized='incremental',
        unique_key=['symbol', 'date'],
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns'
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
    -- PSX trades ~250 days/year, so a 500-calendar-day buffer is only ~342 trading rows --
    -- not enough to cover the 250 written rows plus a 252-row trailing lookback
    -- (trailing_return_252d) or a 199-row lookback (ma_200 / rolling_vol_200) at the oldest
    -- written row. 750 calendar days comfortably covers 250 (write) + 252 (longest lookback)
    -- + margin for non-trading days (holidays/weekends already excluded upstream).
    and date >= cast({{ dbt.dateadd('day', -750, 'current_date') }} as date)
    {% endif %}

),

ema_base as (

    select
        symbol,
        date,
        close,
        {{ truncated_ema('close', '2.0/13', 90) }} as ema_12,
        {{ truncated_ema('close', '2.0/27', 180) }} as ema_26
    from base

),

macd_line_calc as (

    select
        symbol,
        date,
        ema_12 - ema_26 as macd_line
    from ema_base

),

macd_signal_calc as (

    select
        symbol,
        date,
        macd_line,
        {{ truncated_ema('macd_line', '0.2', 90) }} as macd_signal
    from macd_line_calc

),

bollinger as (

    select
        symbol,
        date,
        avg(close) over (
            partition by symbol order by date rows between 19 preceding and current row
        ) as bollinger_mid,
        avg(close) over (
            partition by symbol order by date rows between 19 preceding and current row
        ) + 2 * stddev(close) over (
            partition by symbol order by date rows between 19 preceding and current row
        ) as bollinger_upper,
        avg(close) over (
            partition by symbol order by date rows between 19 preceding and current row
        ) - 2 * stddev(close) over (
            partition by symbol order by date rows between 19 preceding and current row
        ) as bollinger_lower
    from base

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
        coalesce(greatest(close - lag(close) over (partition by symbol order by date), 0), 0) as gain,
        coalesce(greatest(lag(close) over (partition by symbol order by date) - close, 0), 0) as loss
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
        macd.macd_line,
        macd.macd_signal,
        macd.macd_line - macd.macd_signal as macd_histogram,
        b.bollinger_upper,
        b.bollinger_mid,
        b.bollinger_lower,
        m.rolling_vol_20,
        m.rolling_vol_50,
        m.rolling_vol_200,
        m.trailing_return_5d,
        m.trailing_return_252d
    from moving_averages m
    inner join rsi r on m.symbol = r.symbol and m.date = r.date
    inner join macd_signal_calc macd on m.symbol = macd.symbol and m.date = macd.date
    inner join bollinger b on m.symbol = b.symbol and m.date = b.date

)

select *
from final
{% if is_incremental() %}
where date >= cast({{ dbt.dateadd('day', -250, 'current_date') }} as date)
{% endif %}
