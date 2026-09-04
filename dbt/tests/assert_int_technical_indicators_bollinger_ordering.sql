-- warehouse/dbt/tests/assert_int_technical_indicators_bollinger_ordering.sql
-- Fails (returns rows) if bollinger_upper < bollinger_mid or bollinger_mid < bollinger_lower anywhere.
select symbol, date, bollinger_upper, bollinger_mid, bollinger_lower
from {{ ref('int_technical_indicators') }}
where bollinger_upper < bollinger_mid
   or bollinger_mid < bollinger_lower
