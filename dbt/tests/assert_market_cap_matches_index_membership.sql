{{ config(severity='warn') }}

-- Currently vacuous: raw.screener.market_cap is NULL/zero for all 745 rows
-- (verified Task 11 review), so fact_valuation_daily.market_cap has no
-- non-null/non-zero values to compare and this test trivially passes with
-- zero comparable pairs. That's an upstream extract/ layer gap, out of
-- scope for this dbt plan.
--
-- When that upstream gap is eventually fixed, this comparison will ALSO
-- need a unit-scale correction before it means anything:
-- fact_index_membership.market_cap_m is in millions (verified range
-- 162-437,244), while stg_screener.market_cap (and therefore
-- fact_valuation_daily.market_cap) is documented as the raw/absolute
-- value, not millions. Comparing them directly with a > 1.0 tolerance, as
-- this test does today, will fire on essentially every row for a pure
-- unit-scale mismatch, not genuine endpoint disagreement. Whoever revisits
-- this after the NULL/zero gap is fixed needs to divide one side by
-- 1,000,000 (or otherwise normalize units) before re-enabling this as a
-- meaningful check.
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
