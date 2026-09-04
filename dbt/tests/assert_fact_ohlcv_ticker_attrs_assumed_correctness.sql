select fact_ohlcv.symbol, fact_ohlcv.date, fact_ohlcv.ticker_key
from {{ ref('fact_ohlcv') }} fact_ohlcv
join {{ ref('dim_tickers') }} dim_tickers
    on fact_ohlcv.ticker_key = dim_tickers.dbt_scd_id
    and fact_ohlcv.symbol = dim_tickers.symbol
where fact_ohlcv.is_ticker_attrs_assumed = false
  and not (
      fact_ohlcv.date >= cast(dim_tickers.dbt_valid_from as date)
      and (fact_ohlcv.date < cast(dim_tickers.dbt_valid_to as date) or dim_tickers.dbt_valid_to is null)
  )
