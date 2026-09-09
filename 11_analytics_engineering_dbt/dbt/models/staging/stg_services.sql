-- The only staging model that drops rows, and it does so loudly.
--
-- Decision: exact duplicates are removed here, because a duplicate
-- delivery of the same source row is a transport defect, not a fact about
-- the world. Everything else that is wrong -- negative durations, orphan
-- keys, unknown codes -- is KEPT and caught by tests. Silently dropping
-- bad rows would make the tests pass and the problem invisible.

with source as (
    select * from {{ ref('raw_services') }}
),

renamed as (
    select
        service_id,
        client_id,
        staff_id,
        cast(service_date as date)          as service_date,
        service_type_code,
        cast(duration_minutes as integer)   as duration_minutes
    from source
),

deduplicated as (
    select distinct * from renamed
)

select
    *,
    round(duration_minutes / 60.0, 4) as duration_hours
from deduplicated
