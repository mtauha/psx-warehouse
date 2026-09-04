{{
    config(
        materialized='incremental',
        unique_key=['symbol', 'date'],
        incremental_strategy='delete+insert'
    )
}}

with indicators as (

    select *
    from {{ ref('int_technical_indicators') }}
    {% if is_incremental() %}
    where date >= {{ dbt.dateadd('day', -250, 'current_date') }}
    {% endif %}

),

indicators_with_crossover as (

    select
        *,
        case
            when lag(sign(ma_50 - ma_200)) over (partition by symbol order by date) <= 0
                 and sign(ma_50 - ma_200) > 0 then 'golden_cross'
            when lag(sign(ma_50 - ma_200)) over (partition by symbol order by date) >= 0
                 and sign(ma_50 - ma_200) < 0 then 'death_cross'
            else null
        end as ma_crossover_event
    from indicators

),

drawdown as (

    select *
    from {{ ref('int_drawdown') }}
    {% if is_incremental() %}
    where date >= {{ dbt.dateadd('day', -250, 'current_date') }}
    {% endif %}

),

ohlcv as (

    select symbol, date, ticker_key
    from {{ ref('fact_ohlcv') }}
    {% if is_incremental() %}
    where date >= {{ dbt.dateadd('day', -250, 'current_date') }}
    {% endif %}

)

select
    o.ticker_key,
    i.symbol,
    i.date,
    i.daily_return_pct,
    i.ma_20,
    i.ma_50,
    i.ma_200,
    i.rsi_14,
    i.macd_line,
    i.macd_signal,
    i.macd_histogram,
    i.bollinger_upper,
    i.bollinger_mid,
    i.bollinger_lower,
    i.rolling_vol_20,
    i.rolling_vol_50,
    i.rolling_vol_200,
    i.trailing_return_5d,
    i.trailing_return_252d,
    d.max_drawdown_pct,
    i.ma_crossover_event
from indicators_with_crossover i
left join drawdown d on i.symbol = d.symbol and i.date = d.date
left join ohlcv o on i.symbol = o.symbol and i.date = o.date
