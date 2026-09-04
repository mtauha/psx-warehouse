{{ config(severity='warn') }}

select *
from {{ ref('fact_ohlcv') }}
where is_ticker_attrs_assumed = true
