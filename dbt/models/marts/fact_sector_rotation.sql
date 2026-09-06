{{ config(materialized='table') }}

with sector as (

    select sector_code, date, trailing_return_63d as sector_return_63d
    from {{ ref('int_sector_returns') }}

),

market as (

    select date, trailing_return_63d as market_trailing_return_63d
    from {{ ref('int_market_returns') }}

),

joined as (

    select
        s.sector_code,
        s.date,
        s.sector_return_63d,
        s.sector_return_63d - m.market_trailing_return_63d as relative_strength_vs_market_63d
    from sector s
    left join market m on s.date = m.date

)

select
    sector_code,
    date,
    sector_return_63d,
    relative_strength_vs_market_63d,
    case when relative_strength_vs_market_63d is not null
        then rank() over (
            partition by date, (relative_strength_vs_market_63d is null)
            order by relative_strength_vs_market_63d desc
        )
    end as rotation_rank,
    case when relative_strength_vs_market_63d is not null
        then ntile(5) over (
            partition by date, (relative_strength_vs_market_63d is null)
            order by relative_strength_vs_market_63d desc
        )
    end as rotation_quintile
from joined
