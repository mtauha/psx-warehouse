{{
    config(
        materialized='incremental',
        unique_key=['sector_code_a', 'sector_code_b', 'date'],
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns'
    )
}}

with sector_returns as (

    select sector_code, date, daily_return_pct
    from {{ ref('int_sector_returns') }}
    {% if is_incremental() %}
    where date >= cast({{ dbt.dateadd('day', -750, 'current_date') }} as date)
    {% endif %}

),

pairs as (

    select
        a.sector_code as sector_code_a,
        b.sector_code as sector_code_b,
        a.date,
        a.daily_return_pct as return_a,
        b.daily_return_pct as return_b
    from sector_returns a
    inner join sector_returns b
        on a.date = b.date
        and a.sector_code < b.sector_code

),

windowed as (

    select
        sector_code_a,
        sector_code_b,
        date,
        corr(return_a, return_b) over (
            partition by sector_code_a, sector_code_b order by date rows between 251 preceding and current row
        ) as correlation_raw
    from pairs

)

select
    sector_code_a,
    sector_code_b,
    date,
    case when correlation_raw between -1 and 1 then correlation_raw else null end as correlation_252d
from windowed
{% if is_incremental() %}
where date >= cast({{ dbt.dateadd('day', -250, 'current_date') }} as date)
{% endif %}
