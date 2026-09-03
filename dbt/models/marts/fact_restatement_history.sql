with versions as (

    select
        symbol,
        date,
        count(*) as restatement_count,
        min(loaded_at) as first_loaded_at,
        max(loaded_at) as last_loaded_at
    from {{ ref('stg_stock_history') }}
    group by symbol, date

)

select
    coalesce(real_match.dbt_scd_id, earliest_match.dbt_scd_id) as ticker_key,
    versions.symbol,
    versions.date,
    versions.restatement_count,
    versions.first_loaded_at,
    versions.last_loaded_at,
    case
        when real_match.dbt_scd_id is not null then false
        when earliest_match.dbt_scd_id is not null then true
        else null
    end as is_ticker_attrs_assumed
from versions
{{ as_of_ticker_join('versions', 'date') }}
