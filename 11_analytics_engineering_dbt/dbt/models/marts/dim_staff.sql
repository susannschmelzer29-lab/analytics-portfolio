with staff as (
    select * from {{ ref('stg_staff') }}
),

centres as (
    select * from {{ ref('stg_cost_centres') }}
)

select
    s.staff_id,
    s.role,
    s.cost_centre_id,
    c.cost_centre_name,
    c.funding_source,
    s.contract_hours_week,
    s.fte_share,
    s.start_date,
    s.end_date,
    (s.end_date is null) as is_active
from staff s
left join centres c on s.cost_centre_id = c.cost_centre_id
