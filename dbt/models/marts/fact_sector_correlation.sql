select
    sector_code_a,
    sector_code_b,
    date,
    correlation_252d
from {{ ref('int_sector_correlation') }}
