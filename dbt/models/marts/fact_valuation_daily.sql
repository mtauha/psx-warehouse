select
    stg.symbol,
    stg.snapshot_date as date,
    dim_tickers.dbt_scd_id as ticker_key,
    stg.market_cap,
    stg.price,
    stg.pe_ratio,
    stg.dividend_yield,
    stg.free_float,
    stg.volume_avg_30d,
    stg.change_1y_pct,
    stg.listed_in
from {{ ref('stg_screener') }} as stg
left join {{ ref('dim_tickers') }} as dim_tickers
    on stg.symbol = dim_tickers.symbol
    and stg.snapshot_date >= cast(dim_tickers.dbt_valid_from as date)
    and (stg.snapshot_date < cast(dim_tickers.dbt_valid_to as date) or dim_tickers.dbt_valid_to is null)
