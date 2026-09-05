{{ config(materialized='table') }}

with market_level as (

    -- current_index is documented as identical across every constituent row for
    -- a given day, but first_value(... order by symbol) picks one deterministic
    -- value per date rather than assuming that - a GROUP BY here would silently
    -- produce more than one row per date (breaking this model's grain) if that
    -- assumption ever turns out to be wrong for some row.
    select distinct
        snapshot_date as date,
        first_value(current_index) over (
            partition by snapshot_date order by symbol
        ) as current_index
    from {{ ref('int_index_constituents_pit') }}
    where index_name = 'KSE100'  -- hardcoded per Global Constraints: this project's extraction is currently scoped to a single tracked index (extract/config.py's INDEX_NAMES default), but that's a config default, not a schema guarantee - don't assume it's the only row forever
        and current_index is not null

),

returns as (

    select
        date,
        current_index,
        (current_index - lag(current_index) over (order by date))
            / lag(current_index) over (order by date) as daily_return_pct
    from market_level

)

select
    date,
    current_index,
    daily_return_pct,
    (current_index - lag(current_index, 63) over (order by date))
        / lag(current_index, 63) over (order by date) as trailing_return_63d
from returns
