with clients as (
    select * from {{ ref('stg_clients') }}
)

select
    client_id,
    entry_date,
    exit_date,
    care_level,
    district,
    (exit_date is null)                                     as is_active,
    date_diff('day', entry_date, coalesce(exit_date, date '{{ var("reporting_end") }}'))
                                                            as days_in_care
from clients
