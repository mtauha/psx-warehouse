{{ config(severity='warn') }}

-- fact_sector_daily's dedup (row_number() over the grain, latest loaded_at
-- wins) is only safe because today's duplicate loads carry identical values.
-- The raw loader inserts unconditionally with no dedup guarantee, so nothing
-- else enforces that premise. This flags any grain where a same-day re-scrape
-- picked up genuinely different values - a signal the dedup tiebreak is now
-- making a real choice, not just discarding an exact repeat.
with grains as (

    select
        sector_code,
        snapshot_date,
        count(*) as n_rows,
        count(distinct coalesce(cast(advance as {{ dbt.type_string() }}), '~null~')) as n_advance,
        count(distinct coalesce(cast(decline as {{ dbt.type_string() }}), '~null~')) as n_decline,
        count(distinct coalesce(cast(unchanged as {{ dbt.type_string() }}), '~null~')) as n_unchanged,
        count(distinct coalesce(cast(turnover as {{ dbt.type_string() }}), '~null~')) as n_turnover,
        count(distinct coalesce(cast(market_cap_b as {{ dbt.type_string() }}), '~null~')) as n_market_cap_b
    from {{ ref('stg_sectors') }}
    group by sector_code, snapshot_date

)

select *
from grains
where n_rows > 1
  and (
      n_advance > 1
      or n_decline > 1
      or n_unchanged > 1
      or n_turnover > 1
      or n_market_cap_b > 1
  )
