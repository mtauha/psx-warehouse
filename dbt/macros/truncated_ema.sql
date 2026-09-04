-- warehouse/dbt/macros/truncated_ema.sql
{% macro truncated_ema(value_column, alpha, window_size, partition_column='symbol', order_column='date') %}
(
    (
        {%- for k in range(window_size) %}
        coalesce(
            lag({{ value_column }}, {{ k }}) over (partition by {{ partition_column }} order by {{ order_column }}),
            0
        ) * power(1 - ({{ alpha }}), {{ k }})
        {%- if not loop.last %} +
        {% endif -%}
        {%- endfor %}
    )
    /
    nullif(
    (
        {%- for k in range(window_size) %}
        case
            when lag({{ value_column }}, {{ k }}) over (partition by {{ partition_column }} order by {{ order_column }}) is not null
            then power(1 - ({{ alpha }}), {{ k }})
            else 0
        end
        {%- if not loop.last %} +
        {% endif -%}
        {%- endfor %}
    ), 0)
)
{% endmacro %}
