-- Grain: exactly one row per delivered service event.
--
-- Stating the grain is not documentation garnish. Every additive measure
-- below is only correct because the grain holds, and the uniqueness test
-- on service_id is what keeps it holding.

select
    service_id,
    client_id,
    staff_id,
    cost_centre_id,
    service_type_code,

    service_date,
    date_trunc('month', service_date)::date as month_start,

    duration_minutes,
    duration_hours,
    is_billable,
    billable_amount_eur,

    staff_role,
    cost_centre_name,
    funding_source,
    has_orphan_reference
from {{ ref('int_services_enriched') }}
