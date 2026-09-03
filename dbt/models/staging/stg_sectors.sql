select
    sector_code,
    sector_name,
    advance,
    decline,
    unchanged,
    turnover,
    market_cap_b,
    snapshot_date,
    loaded_at
from {{ source('raw', 'sectors') }}
