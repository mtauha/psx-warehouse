-- Fails if any date's momentum rank exceeds that date's actual point-in-time
-- KSE-100 constituent count - catches a join fanout or dedup bug immediately
-- rather than downstream.
with universe_size as (

    select snapshot_date as date, count(distinct ticker_key) as n_constituents
    from {{ ref('int_index_constituents_pit') }}
    where index_name = 'KSE100'
    group by snapshot_date

)

select r.ticker_key, r.date, r.momentum_63d_rank, u.n_constituents
from {{ ref('fact_cross_sectional_rankings') }} r
inner join universe_size u on r.date = u.date
where r.momentum_63d_rank > u.n_constituents
