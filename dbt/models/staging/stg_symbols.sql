with symbols as (

    select
        ticker_attr_id,
        symbol,
        name,
        sector_name,
        is_etf,
        is_debt,
        is_gem,
        is_margin_eligible,
        is_latest,
        loaded_at,
        superseded_at
    from {{ source('raw', 'symbols') }}

),

-- One row per sector_code, using each code's most recently seen name --
-- sector names are effectively static, but if raw.sectors ever carries
-- more than one name for the same code across days (a mid-year rename),
-- the latest snapshot wins rather than an arbitrary row.
sector_map as (

    select
        sector_code,
        sector_name,
        row_number() over (
            partition by upper(trim(sector_name))
            order by snapshot_date desc
        ) as rn
    from {{ ref('stg_sectors') }}

)

select
    symbols.ticker_attr_id,
    symbols.symbol,
    symbols.name,
    sector_map.sector_code,
    symbols.is_etf,
    symbols.is_debt,
    symbols.is_gem,
    symbols.is_margin_eligible,
    symbols.is_latest,
    symbols.loaded_at,
    symbols.superseded_at
from symbols
left join sector_map
    on upper(trim(symbols.sector_name)) = upper(trim(sector_map.sector_name))
    and sector_map.rn = 1
