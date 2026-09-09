-- The mirror case: work recorded after the client left.

{{ config(severity='warn', store_failures=true) }}
select
    f.service_id,
    f.client_id,
    f.service_date,
    c.exit_date
from {{ ref('fct_service_delivery') }} f
join {{ ref('dim_client') }} c on f.client_id = c.client_id
where c.exit_date is not null
  and f.service_date > c.exit_date
