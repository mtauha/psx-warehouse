select
    history_id,
    symbol,
    date,
    open,
    high,
    low,
    close,
    volume,
    is_anomaly,
    row_hash,
    is_latest,
    loaded_at,
    superseded_at
from {{ source('raw', 'stock_history') }}
