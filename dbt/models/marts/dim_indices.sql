select distinct
    index_name
from {{ ref('stg_index_constituents') }}
