-- Fails if trailing_return_252d is NULL for a symbol/date that has >= 252 prior trading rows
-- in stg_stock_history (i.e. insufficient buffer, not insufficient real history).
--
-- Note: this test only makes sense against a FULL build (not a narrow incremental one), since
-- it checks the model's steady-state correctness across all of history. Run with
-- `dbt build --full-refresh --select int_technical_indicators+` to verify it meaningfully.
with row_counts as (
    select
        symbol,
        date,
        row_number() over (partition by symbol order by date) as rn
    from {{ ref('stg_stock_history') }}
    where is_latest = true
)
select
    t.symbol,
    t.date,
    t.trailing_return_252d
from {{ ref('int_technical_indicators') }} t
inner join row_counts r on t.symbol = r.symbol and t.date = r.date
where r.rn > 252
  and t.trailing_return_252d is null
