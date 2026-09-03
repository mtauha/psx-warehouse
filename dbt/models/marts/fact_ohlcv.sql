with ohlcv as (

    select *
    from {{ ref('stg_stock_history') }}
    where is_latest = true

)

select
    coalesce(real_match.dbt_scd_id, earliest_match.dbt_scd_id) as ticker_key,
    ohlcv.symbol,
    ohlcv.date,
    ohlcv.open,
    ohlcv.high,
    ohlcv.low,
    ohlcv.close,
    ohlcv.volume,
    ohlcv.is_anomaly,
    case
        when real_match.dbt_scd_id is not null then false
        when earliest_match.dbt_scd_id is not null then true
        else null
    end as is_ticker_attrs_assumed
from ohlcv
{{ as_of_ticker_join('ohlcv', 'date') }}
