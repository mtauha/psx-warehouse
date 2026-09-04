-- raw.screener can carry exact duplicate loads for the same
-- (symbol, snapshot_date) when the scraper runs more than once
-- in a day; keep only the most recently loaded row per grain key so the
-- model's declared grain holds.
with deduped as (

    select
        *,
        row_number() over (
            partition by symbol, snapshot_date
            order by loaded_at desc
        ) as rn
    from {{ ref('stg_screener') }}

)

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
from deduped as stg
left join {{ ref('dim_tickers') }} as dim_tickers
    on stg.symbol = dim_tickers.symbol
    and stg.snapshot_date >= cast(dim_tickers.dbt_valid_from as date)
    and (stg.snapshot_date < cast(dim_tickers.dbt_valid_to as date) or dim_tickers.dbt_valid_to is null)
where stg.rn = 1
