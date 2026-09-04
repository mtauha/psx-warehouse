select
    a.symbol,
    a.dbt_scd_id as version_a,
    b.dbt_scd_id as version_b
from {{ ref('dim_tickers') }} a
join {{ ref('dim_tickers') }} b
    on a.symbol = b.symbol
    and a.dbt_scd_id != b.dbt_scd_id
    and a.dbt_valid_from < coalesce(b.dbt_valid_to, {{ dbt.current_timestamp() }})
    and coalesce(a.dbt_valid_to, {{ dbt.current_timestamp() }}) > b.dbt_valid_from
