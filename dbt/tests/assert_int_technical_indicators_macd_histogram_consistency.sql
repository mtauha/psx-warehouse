-- warehouse/dbt/tests/assert_int_technical_indicators_macd_histogram_consistency.sql
-- Fails if macd_histogram isn't (macd_line - macd_signal) within floating-point tolerance.
select symbol, date, macd_line, macd_signal, macd_histogram
from {{ ref('int_technical_indicators') }}
where abs(macd_histogram - (macd_line - macd_signal)) > 0.0001
