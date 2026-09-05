-- Regression test for the zero-variance edge case documented in the spec
-- ("Cross-dialect verification"): a ticker with an unchanged close price for
-- its full 252-row window has zero variance, making beta's denominator
-- exactly 0. Confirms the NULLIF guard actually neutralizes it (NULL, not an
-- error or a garbage value) rather than only checking it in theory.
with constant_price_window as (

    select
        ticker_key,
        min(date) as first_date,
        max(date) as last_date,
        count(*) as n,
        count(distinct close) as n_distinct_close
    from {{ ref('int_ohlcv_pit') }}
    group by ticker_key
    having count(*) >= 252 and count(distinct close) = 1

)

select r.ticker_key, r.date, r.beta_full_252d
from constant_price_window c
inner join {{ ref('int_ticker_relationships') }} r on c.ticker_key = r.ticker_key
where r.date between c.first_date and c.last_date
  and r.beta_full_252d is not null
