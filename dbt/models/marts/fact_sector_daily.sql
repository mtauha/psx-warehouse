select
    sector_code,
    snapshot_date as date,
    advance,
    decline,
    unchanged,
    turnover,
    market_cap_b
from {{ ref('stg_sectors') }}
