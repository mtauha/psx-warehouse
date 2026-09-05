{{ config(materialized='table') }}

with ticker_returns as (

    select
        o.ticker_key,
        o.date,
        o.daily_return_pct,
        dt.sector_code
    from {{ ref('int_ohlcv_pit') }} o
    inner join {{ ref('dim_tickers') }} dt on o.ticker_key = dt.dbt_scd_id

),

weights as (

    select
        ticker_key,
        snapshot_date as date,
        market_cap_m
    from {{ ref('int_index_constituents_pit') }}
    where index_name = 'KSE100'  -- hardcoded per Global Constraints: this project's extraction is currently scoped to a single tracked index (extract/config.py's INDEX_NAMES default), but that's a config default, not a schema guarantee - don't assume it's the only row forever

),

weighted as (

    select
        tr.sector_code,
        tr.date,
        tr.daily_return_pct * w.market_cap_m as weighted_return,
        w.market_cap_m
    from ticker_returns tr
    inner join weights w on tr.ticker_key = w.ticker_key and tr.date = w.date
    where tr.daily_return_pct is not null
      and w.market_cap_m is not null
      and w.market_cap_m > 0

),

sector_return as (

    select
        sector_code,
        date,
        sum(weighted_return) / sum(market_cap_m) as daily_return_pct
    from weighted
    group by sector_code, date

)

select
    sector_code,
    date,
    daily_return_pct,
    -- Compounds daily returns forward via log-sum rather than lagging a single
    -- price level (there is no one "sector price" to lag - this is a synthetic
    -- cap-weighted series). The count() guard nulls out incomplete windows
    -- (bootstrap period) instead of silently compounding a partial 63 days.
    case
        when count(daily_return_pct) over (
            partition by sector_code order by date rows between 62 preceding and current row
        ) = 63
        then exp(sum(ln(1 + daily_return_pct)) over (
            partition by sector_code order by date rows between 62 preceding and current row
        )) - 1
        else null
    end as trailing_return_63d
from sector_return
