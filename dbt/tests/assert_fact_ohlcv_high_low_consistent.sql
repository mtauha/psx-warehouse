-- is_anomaly = true rows are excluded: they are the exact rows the source scraper
-- already flags for this same OHLC inconsistency, so re-failing the build on them
-- would be flagging already-known, already-labeled data rather than a new integrity
-- issue. This test guards against unflagged/new violations only.
select *
from {{ ref('fact_ohlcv') }}
where is_anomaly = false
  and not (high >= low and high >= open and high >= close and low <= open and low <= close)
