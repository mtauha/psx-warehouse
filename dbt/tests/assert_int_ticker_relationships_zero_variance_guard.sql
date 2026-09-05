-- Regression test for the zero-variance edge case documented in the spec
-- ("Cross-dialect verification"): a ticker with an unchanged close price for
-- its full 252-row window has zero variance IN ITS OWN return series, making
-- corr_vs_index_252d/corr_vs_sector_252d mathematically undefined (0/0).
-- This is NOT the same edge case as beta: beta's denominator is the MARKET's
-- variance, not the ticker's, so a constant ticker price does not zero
-- beta's denominator at all - it correctly produces a well-defined
-- beta of exactly 0 (covar_samp(constant, X) = 0 for any X, mathematically),
-- not NULL. An earlier version of this test checked beta_full_252d for this
-- reason and was wrong - caught during Task 6's review, corrected here.
-- Confirms the BETWEEN -1 AND 1 guard actually neutralizes the undefined
-- correlation into NULL (not NaN, not an error, not a garbage value) rather
-- than only checking it in theory.
with constant_price_window as (

    select
        ticker_key,
        min(date) as first_date,
        max(date) as last_date
    from {{ ref('int_ohlcv_pit') }}
    group by ticker_key
    having count(*) >= 252 and count(distinct close) = 1

)

select r.ticker_key, r.date, r.corr_vs_index_252d, r.corr_vs_sector_252d
from constant_price_window c
inner join {{ ref('int_ticker_relationships') }} r on c.ticker_key = r.ticker_key
where r.date between c.first_date and c.last_date
  and (r.corr_vs_index_252d is not null or r.corr_vs_sector_252d is not null)
