-- raw.index_constituents can carry exact duplicate loads for the same
-- (index_name, symbol, snapshot_date) when the scraper runs more than once
-- in a day; keep only the most recently loaded row per grain key so the
-- model's declared grain holds.
with deduped as (

    select
        *,
        row_number() over (
            partition by index_name, symbol, snapshot_date
            order by loaded_at desc
        ) as rn
    from {{ ref('stg_index_constituents') }}

)

select
    stg.index_name,
    stg.symbol,
    stg.snapshot_date,
    dim_tickers.dbt_scd_id as ticker_key,
    stg.current_index,
    stg.idx_weight,
    stg.idx_point,
    stg.market_cap_m,
    stg.freefloat_m,
    stg.shares_m
from deduped as stg
left join {{ ref('dim_tickers') }} as dim_tickers
    on stg.symbol = dim_tickers.symbol
    and stg.snapshot_date >= cast(dim_tickers.dbt_valid_from as date)
    and (stg.snapshot_date < cast(dim_tickers.dbt_valid_to as date) or dim_tickers.dbt_valid_to is null)
where stg.rn = 1
