{{ config(severity='warn') }}

-- fact_index_membership's dedup (row_number() over the grain, latest loaded_at
-- wins) is only safe because today's duplicate loads carry identical values.
-- The raw loader inserts unconditionally with no dedup guarantee, so nothing
-- else enforces that premise. This flags any grain where a same-day re-scrape
-- picked up genuinely different values - a signal the dedup tiebreak is now
-- making a real choice, not just discarding an exact repeat.
with grains as (

    select
        index_name,
        symbol,
        snapshot_date,
        count(*) as n_rows,
        count(distinct coalesce(cast(current_index as {{ dbt.type_string() }}), '~null~')) as n_current_index,
        count(distinct coalesce(cast(idx_weight as {{ dbt.type_string() }}), '~null~')) as n_idx_weight,
        count(distinct coalesce(cast(idx_point as {{ dbt.type_string() }}), '~null~')) as n_idx_point,
        count(distinct coalesce(cast(market_cap_m as {{ dbt.type_string() }}), '~null~')) as n_market_cap_m,
        count(distinct coalesce(cast(freefloat_m as {{ dbt.type_string() }}), '~null~')) as n_freefloat_m,
        count(distinct coalesce(cast(shares_m as {{ dbt.type_string() }}), '~null~')) as n_shares_m
    from {{ ref('stg_index_constituents') }}
    group by index_name, symbol, snapshot_date

)

select *
from grains
where n_rows > 1
  and (
      n_current_index > 1
      or n_idx_weight > 1
      or n_idx_point > 1
      or n_market_cap_m > 1
      or n_freefloat_m > 1
      or n_shares_m > 1
  )
