-- raw.sectors can carry exact duplicate loads for the same
-- (sector_code, snapshot_date) when the scraper runs more than once
-- in a day; keep only the most recently loaded row per grain key so the
-- model's declared grain holds.
with deduped as (

    select
        *,
        row_number() over (
            partition by sector_code, snapshot_date
            order by loaded_at desc
        ) as rn
    from {{ ref('stg_sectors') }}

)

select
    sector_code,
    snapshot_date as date,
    advance,
    decline,
    unchanged,
    turnover,
    market_cap_b
from deduped
where rn = 1
