-- For a (symbol, date) that has never been restated, the point-in-time close
-- and the latest-known close must be identical - proves int_ohlcv_pit isn't
-- drifting from fact_ohlcv for reasons unrelated to restatement.
select
    p.symbol,
    p.date,
    p.close as pit_close,
    f.close as fact_close
from {{ ref('int_ohlcv_pit') }} p
inner join {{ ref('fact_ohlcv') }} f on p.symbol = f.symbol and p.date = f.date
inner join {{ ref('fact_restatement_history') }} rh on rh.symbol = p.symbol and rh.date = p.date
where rh.restatement_count = 1
  and p.close != f.close
