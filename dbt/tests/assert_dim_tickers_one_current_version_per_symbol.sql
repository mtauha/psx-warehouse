select symbol, count(*) as current_version_count
from {{ ref('dim_tickers') }}
where dbt_valid_to is null
group by symbol
having count(*) > 1
