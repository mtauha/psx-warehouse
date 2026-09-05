select *
from {{ ref('fact_cross_sectional_rankings') }}
where date > {% if target.type == 'bigquery' %}current_date('Asia/Karachi'){% else %}current_date{% endif %}
