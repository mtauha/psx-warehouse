-- Point-in-time-safe index constituent snapshot: first-observed row per
-- (index_name, symbol, snapshot_date), not the most-recently-loaded row
-- fact_index_membership uses. Mirrors the dedup pattern but with
-- order by loaded_at asc instead of desc.
with deduped as (

    select
        *,
        row_number() over (
            partition by index_name, symbol, snapshot_date
            order by loaded_at asc
        ) as rn
    from {{ ref('stg_index_constituents') }}

)

select
    stg.index_name,
    stg.symbol,
    stg.snapshot_date,
    coalesce(real_match.dbt_scd_id, earliest_match.dbt_scd_id) as ticker_key,
    stg.current_index,
    stg.idx_weight,
    stg.idx_point,
    stg.market_cap_m,
    stg.freefloat_m,
    stg.shares_m
from deduped as stg
{{ as_of_ticker_join('stg', 'snapshot_date') }}
where stg.rn = 1
