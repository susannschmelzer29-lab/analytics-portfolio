with source as (
    select * from {{ ref('raw_service_types') }}
)

select
    service_type_code,
    trim(name)                                  as service_type_name,
    cast(is_billable as boolean)                as is_billable,
    cast(rate_per_hour_eur as decimal(8,2))     as rate_per_hour_eur
from source
