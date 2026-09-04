{% snapshot dim_tickers %}

{{
    config(
        target_schema=target.schema,
        unique_key='symbol',
        strategy='check',
        check_cols=['name', 'sector_code', 'is_etf', 'is_debt', 'is_gem', 'is_margin_eligible'],
        hard_deletes='invalidate',
    )
}}

select
    symbol,
    name,
    sector_code,
    is_etf,
    is_debt,
    is_gem,
    is_margin_eligible
from {{ ref('stg_symbols') }}
where is_latest = true

{% endsnapshot %}
