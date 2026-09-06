-- pe_ratio_rank/quintile must be NULL exactly when pe_ratio is NULL or <= 0 -
-- ties the exclusion rule to the actual output so a future refactor can't
-- silently drop the filter.
select ticker_key, date, pe_ratio, pe_ratio_rank, pe_ratio_quintile
from {{ ref('fact_cross_sectional_rankings') }}
where (pe_ratio is null or pe_ratio <= 0)
  and (pe_ratio_rank is not null or pe_ratio_quintile is not null)
