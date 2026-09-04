select fact_restatement_history.symbol, fact_restatement_history.date, fact_restatement_history.ticker_key
from {{ ref('fact_restatement_history') }} fact_restatement_history
join {{ ref('dim_tickers') }} dim_tickers
    on fact_restatement_history.ticker_key = dim_tickers.dbt_scd_id
    and fact_restatement_history.symbol = dim_tickers.symbol
where fact_restatement_history.is_ticker_attrs_assumed = false
  and not (
      fact_restatement_history.date >= cast(dim_tickers.dbt_valid_from as date)
      and (fact_restatement_history.date < cast(dim_tickers.dbt_valid_to as date) or dim_tickers.dbt_valid_to is null)
  )
