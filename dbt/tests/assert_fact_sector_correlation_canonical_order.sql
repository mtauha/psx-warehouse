select *
from {{ ref('fact_sector_correlation') }}
where sector_code_a >= sector_code_b
