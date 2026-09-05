{{
    config(
        materialized='incremental',
        unique_key=['ticker_key', 'date'],
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns'
    )
}}

with ticker_returns as (

    select
        o.ticker_key,
        o.symbol,
        o.date,
        o.daily_return_pct as stock_return,
        dt.sector_code
    from {{ ref('int_ohlcv_pit') }} o
    inner join {{ ref('dim_tickers') }} dt on o.ticker_key = dt.dbt_scd_id
    {% if is_incremental() %}
    -- Same 750-calendar-day buffer sizing as int_ohlcv_pit, sized for the
    -- 251-row (252-trading-day) beta/correlation lookback below.
    where o.date >= cast({{ dbt.dateadd('day', -750, 'current_date') }} as date)
    {% endif %}

),

with_market_and_sector as (

    select
        tr.ticker_key,
        tr.symbol,
        tr.date,
        tr.stock_return,
        m.daily_return_pct as market_return,
        sr.daily_return_pct as sector_return
    from ticker_returns tr
    left join {{ ref('int_market_returns') }} m on tr.date = m.date
    left join {{ ref('int_sector_returns') }} sr on tr.sector_code = sr.sector_code and tr.date = sr.date

)
,

windowed as (

    select
        ticker_key,
        symbol,
        date,
        covar_samp(stock_return, market_return) over (
            partition by ticker_key order by date rows between 251 preceding and current row
        )
            / nullif(var_samp(market_return) over (
                partition by ticker_key order by date rows between 251 preceding and current row
            ), 0) as beta_full_252d,
        covar_samp(
            case when market_return >= 0 then stock_return end,
            case when market_return >= 0 then market_return end
        ) over (
            partition by ticker_key order by date rows between 251 preceding and current row
        )
            / nullif(var_samp(case when market_return >= 0 then market_return end) over (
                partition by ticker_key order by date rows between 251 preceding and current row
            ), 0) as beta_upside_252d,
        covar_samp(
            case when market_return < 0 then stock_return end,
            case when market_return < 0 then market_return end
        ) over (
            partition by ticker_key order by date rows between 251 preceding and current row
        )
            / nullif(var_samp(case when market_return < 0 then market_return end) over (
                partition by ticker_key order by date rows between 251 preceding and current row
            ), 0) as beta_downside_252d,
        corr(stock_return, market_return) over (
            partition by ticker_key order by date rows between 251 preceding and current row
        ) as corr_vs_index_raw,
        corr(stock_return, sector_return) over (
            partition by ticker_key order by date rows between 251 preceding and current row
        ) as corr_vs_sector_raw
    from with_market_and_sector

)

select
    ticker_key,
    symbol,
    date,
    beta_full_252d,
    beta_upside_252d,
    beta_downside_252d,
    case when corr_vs_index_raw between -1 and 1 then corr_vs_index_raw else null end as corr_vs_index_252d,
    case when corr_vs_sector_raw between -1 and 1 then corr_vs_sector_raw else null end as corr_vs_sector_252d
from windowed
{% if is_incremental() %}
where date >= cast({{ dbt.dateadd('day', -250, 'current_date') }} as date)
{% endif %}
