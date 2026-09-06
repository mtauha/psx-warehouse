select
    index_name,
    date,
    open,
    high,
    low,
    close,
    volume,
    change_pct
from {{ ref('stg_index_price_history') }}
