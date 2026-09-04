{{ config(severity='warn') }}

select *
from {{ ref('fact_restatement_history') }}
where is_ticker_attrs_assumed = true
