select *
from {{ ref('fact_ohlcv') }}
where date > {% if target.type == 'bigquery' %}current_date('Asia/Karachi'){% else %}current_date{% endif %}
