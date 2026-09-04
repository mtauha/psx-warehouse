{% macro as_of_ticker_join(fact_alias, date_column) %}

    left join {{ ref('dim_tickers') }} as real_match
        on {{ fact_alias }}.symbol = real_match.symbol
        and {{ fact_alias }}.{{ date_column }} >= cast(real_match.dbt_valid_from as date)
        and (
            {{ fact_alias }}.{{ date_column }} < cast(real_match.dbt_valid_to as date)
            or real_match.dbt_valid_to is null
        )

    left join (
        select
            symbol,
            dbt_scd_id,
            name,
            sector_code,
            is_etf,
            is_debt,
            is_gem,
            is_margin_eligible,
            row_number() over (partition by symbol order by dbt_valid_from asc) as rn
        from {{ ref('dim_tickers') }}
    ) as earliest_match
        on {{ fact_alias }}.symbol = earliest_match.symbol
        and earliest_match.rn = 1
        and real_match.dbt_scd_id is null

{% endmacro %}
