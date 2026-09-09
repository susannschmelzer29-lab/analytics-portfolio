-- Negative or zero minutes means a sign error or an aborted entry.
-- Kept out of the aggregates by a WHERE clause in the marts, but it must
-- still be reported -- a silently filtered row is a hidden problem.

{{ config(severity='warn', store_failures=true) }}
select
    service_id,
    client_id,
    duration_minutes
from {{ ref('fct_service_delivery') }}
where duration_minutes <= 0
