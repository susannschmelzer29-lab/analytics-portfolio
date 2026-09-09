-- A service delivered before the client was admitted is impossible.
-- Usually a date-format defect in the source export, occasionally a
-- backdated record. Either way somebody has to look at it.

{{ config(severity='warn', store_failures=true) }}
select
    f.service_id,
    f.client_id,
    f.service_date,
    c.entry_date
from {{ ref('fct_service_delivery') }} f
join {{ ref('dim_client') }} c on f.client_id = c.client_id
where f.service_date < c.entry_date
