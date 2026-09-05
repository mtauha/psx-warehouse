{{
    config(
        materialized='incremental',
        unique_key=['ticker_key', 'date'],
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns'
    )
}}

with universe as (

    -- Point-in-time universe: only tickers that were actual KSE-100
    -- constituents on a given date, not today's constituent list - this is
    -- what avoids survivorship bias (see spec's "Universe & scope decisions").
    select distinct ticker_key, snapshot_date as date
    from {{ ref('int_index_constituents_pit') }}
    where index_name = 'KSE100'  -- hardcoded per Global Constraints: this project's extraction is currently scoped to a single tracked index (extract/config.py's INDEX_NAMES default), but that's a config default, not a schema guarantee - don't assume it's the only row forever
        and ticker_key is not null  -- excludes null ticker_key rows from source
    {% if is_incremental() %}
    -- No 252-row lookback needed here (unlike the relationship family) -
    -- ranking only needs that single day's own cross-section, so a small
    -- buffer just covers late-arriving corrections in the last few days.
    and snapshot_date >= cast({{ dbt.dateadd('day', -7, 'current_date') }} as date)
    {% endif %}

),

momentum_and_vol as (

    select ticker_key, date, trailing_return_63d as momentum_63d, rolling_vol_200
    from {{ ref('int_ohlcv_pit') }}

),

market as (

    select date, trailing_return_63d as market_trailing_return_63d
    from {{ ref('int_market_returns') }}

),

value as (

    select ticker_key, date, case when pe_ratio > 0 then pe_ratio end as pe_ratio
    from {{ ref('int_screener_pit') }}

),

joined as (

    select
        u.ticker_key,
        u.date,
        mv.momentum_63d,
        mv.momentum_63d - mk.market_trailing_return_63d as relative_strength_63d,
        v.pe_ratio,
        mv.rolling_vol_200
    from universe u
    left join momentum_and_vol mv on u.ticker_key = mv.ticker_key and u.date = mv.date
    left join market mk on u.date = mk.date
    left join value v on u.ticker_key = v.ticker_key and u.date = v.date

)

select
    ticker_key,
    date,
    momentum_63d,
    case when momentum_63d is not null
        then rank() over (partition by date, (momentum_63d is null) order by momentum_63d desc)
    end as momentum_63d_rank,
    case when momentum_63d is not null
        then ntile(5) over (partition by date, (momentum_63d is null) order by momentum_63d desc)
    end as momentum_63d_quintile,
    relative_strength_63d,
    case when relative_strength_63d is not null
        then rank() over (partition by date, (relative_strength_63d is null) order by relative_strength_63d desc)
    end as relative_strength_63d_rank,
    case when relative_strength_63d is not null
        then ntile(5) over (partition by date, (relative_strength_63d is null) order by relative_strength_63d desc)
    end as relative_strength_63d_quintile,
    pe_ratio,
    case when pe_ratio is not null
        then rank() over (partition by date, (pe_ratio is null) order by pe_ratio asc)
    end as pe_ratio_rank,
    case when pe_ratio is not null
        then ntile(5) over (partition by date, (pe_ratio is null) order by pe_ratio asc)
    end as pe_ratio_quintile,
    rolling_vol_200,
    case when rolling_vol_200 is not null
        then rank() over (partition by date, (rolling_vol_200 is null) order by rolling_vol_200 asc)
    end as low_vol_rank,
    case when rolling_vol_200 is not null
        then ntile(5) over (partition by date, (rolling_vol_200 is null) order by rolling_vol_200 asc)
    end as low_vol_quintile
from joined
