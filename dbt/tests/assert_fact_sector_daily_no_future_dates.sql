select *
from {{ ref('fact_sector_daily') }}
where date > {% if target.type == 'bigquery' %}current_date('Asia/Karachi'){% else %}current_date{% endif %}
