select *
from {{ ref('fact_restatement_history') }}
where date > {% if target.type == 'bigquery' %}current_date('Asia/Karachi'){% else %}current_date{% endif %}
