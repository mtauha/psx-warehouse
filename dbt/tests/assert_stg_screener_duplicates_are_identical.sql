{{ config(severity='warn') }}

-- fact_valuation_daily's dedup (row_number() over the grain, latest loaded_at
-- wins) is only safe because today's duplicate loads carry identical values.
-- The raw loader inserts unconditionally with no dedup guarantee, so nothing
-- else enforces that premise. This flags any grain where a same-day re-scrape
-- picked up genuinely different values - a signal the dedup tiebreak is now
-- making a real choice, not just discarding an exact repeat.
with grains as (

    select
        symbol,
        snapshot_date,
        count(*) as n_rows,
        count(distinct coalesce(cast(sector_code_raw as {{ dbt.type_string() }}), '~null~')) as n_sector_code_raw,
        count(distinct coalesce(cast(listed_in as {{ dbt.type_string() }}), '~null~')) as n_listed_in,
        count(distinct coalesce(cast(market_cap as {{ dbt.type_string() }}), '~null~')) as n_market_cap,
        count(distinct coalesce(cast(price as {{ dbt.type_string() }}), '~null~')) as n_price,
        count(distinct coalesce(cast(pe_ratio as {{ dbt.type_string() }}), '~null~')) as n_pe_ratio,
        count(distinct coalesce(cast(dividend_yield as {{ dbt.type_string() }}), '~null~')) as n_dividend_yield,
        count(distinct coalesce(cast(free_float as {{ dbt.type_string() }}), '~null~')) as n_free_float,
        count(distinct coalesce(cast(volume_avg_30d as {{ dbt.type_string() }}), '~null~')) as n_volume_avg_30d,
        count(distinct coalesce(cast(change_1y_pct as {{ dbt.type_string() }}), '~null~')) as n_change_1y_pct
    from {{ ref('stg_screener') }}
    group by symbol, snapshot_date

)

select *
from grains
where n_rows > 1
  and (
      n_sector_code_raw > 1
      or n_listed_in > 1
      or n_market_cap > 1
      or n_price > 1
      or n_pe_ratio > 1
      or n_dividend_yield > 1
      or n_free_float > 1
      or n_volume_avg_30d > 1
      or n_change_1y_pct > 1
  )
