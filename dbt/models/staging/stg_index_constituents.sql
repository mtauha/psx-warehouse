select
    index_name,
    symbol,
    snapshot_date,
    current_index,
    idx_weight,
    idx_point,
    market_cap_m,
    freefloat_m,
    shares_m,
    loaded_at
from {{ source('raw', 'index_constituents') }}
