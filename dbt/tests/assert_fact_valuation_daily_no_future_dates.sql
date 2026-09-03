select *
from {{ ref('fact_valuation_daily') }}
where date > {% if target.type == 'bigquery' %}current_date('Asia/Karachi'){% else %}current_date{% endif %}
