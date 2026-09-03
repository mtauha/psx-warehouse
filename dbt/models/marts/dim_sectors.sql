select distinct
    sector_code,
    first_value(sector_name) over (
        partition by sector_code order by snapshot_date desc
    ) as sector_name
from {{ ref('stg_sectors') }}
