select
    symbol,
    sector as sector_code_raw,
    listed_in,
    market_cap,
    price,
    pe_ratio,
    dividend_yield,
    free_float,
    volume_avg_30d,
    change_1y_pct,
    snapshot_date,
    loaded_at
from {{ source('raw', 'screener') }}
