select
    ticker_key,
    symbol,
    date,
    beta_full_252d,
    beta_upside_252d,
    beta_downside_252d,
    corr_vs_index_252d,
    corr_vs_sector_252d
from {{ ref('int_ticker_relationships') }}
