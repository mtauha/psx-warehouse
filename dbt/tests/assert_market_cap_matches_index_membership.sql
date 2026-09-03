{{ config(severity='warn') }}

select
    fact_valuation_daily.symbol,
    fact_valuation_daily.date,
    fact_valuation_daily.market_cap,
    fact_index_membership.market_cap_m
from {{ ref('fact_valuation_daily') }} fact_valuation_daily
join {{ ref('fact_index_membership') }} fact_index_membership
    on fact_valuation_daily.symbol = fact_index_membership.symbol
    and fact_valuation_daily.date = fact_index_membership.snapshot_date
where abs(fact_valuation_daily.market_cap - fact_index_membership.market_cap_m) > 1.0
