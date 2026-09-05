with deduped as (

    select
        *,
        row_number() over (
            partition by symbol, snapshot_date order by loaded_at asc
        ) as rn
    from {{ ref('stg_screener') }}

)

select
    stg.symbol,
    stg.snapshot_date as date,
    coalesce(real_match.dbt_scd_id, earliest_match.dbt_scd_id) as ticker_key,
    stg.market_cap,
    stg.price,
    stg.pe_ratio
from deduped as stg
{{ as_of_ticker_join('stg', 'snapshot_date') }}
where stg.rn = 1
