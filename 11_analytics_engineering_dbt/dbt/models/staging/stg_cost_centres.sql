with source as (
    select * from {{ ref('raw_cost_centres') }}
)

select
    cost_centre_id,
    trim(name)              as cost_centre_name,
    trim(funding_source)    as funding_source
from source
