{{ config(severity='warn') }}

select
    fact_valuation_daily.symbol,
    fact_valuation_daily.date,
    fact_valuation_daily.price,
    fact_ohlcv.close
from {{ ref('fact_valuation_daily') }} fact_valuation_daily
join {{ ref('fact_ohlcv') }} fact_ohlcv
    on fact_valuation_daily.symbol = fact_ohlcv.symbol
    and fact_valuation_daily.date = fact_ohlcv.date
where abs(fact_valuation_daily.price - fact_ohlcv.close) > 0.01
