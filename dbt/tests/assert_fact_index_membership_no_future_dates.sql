select *
from {{ ref('fact_index_membership') }}
where snapshot_date > {% if target.type == 'bigquery' %}current_date('Asia/Karachi'){% else %}current_date{% endif %}
