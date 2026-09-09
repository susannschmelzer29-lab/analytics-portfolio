select
    service_type_code,
    service_type_name,
    is_billable,
    rate_per_hour_eur
from {{ ref('stg_service_types') }}
