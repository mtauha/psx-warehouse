{{
    config(
        materialized='table',
        partition_by={'field': 'date', 'data_type': 'date'} if target.type == 'bigquery' else none,
        cluster_by=['symbol'] if target.type == 'bigquery' else none
    )
}}

with base as (

    select
        symbol,
        date,
        close
    from {{ ref('stg_stock_history') }}
    where is_latest = true

),

running_max as (

    select
        symbol,
        date,
        close,
        max(close) over (
            partition by symbol order by date rows between unbounded preceding and current row
        ) as running_max_close
    from base

)

select
    symbol,
    date,
    (close - running_max_close) / running_max_close as max_drawdown_pct
from running_max
