-- Monthly capacity per member of staff, in hours.
--
-- Assumption, and it is an assumption: 4.33 weeks per month and a flat
-- 12 % absence allowance (leave, sickness, training). Both are stated
-- here rather than buried in a dashboard formula, so a controller can
-- argue with them.

{% set weeks_per_month = 4.33 %}
{% set absence_allowance = 0.12 %}

with months as (
    select
        cast(range as date) as month_start
    from range(
        date '{{ var("reporting_start") }}',
        date '{{ var("reporting_end") }}' + interval 1 day,
        interval 1 month
    )
),

staff as (
    select * from {{ ref('stg_staff') }}
),

matched as (
    select
        s.staff_id,
        s.cost_centre_id,
        s.role,
        m.month_start,
        s.contract_hours_week,
        s.fte_share
    from staff s
    cross join months m
    -- Only months in which the person was actually employed. Counting
    -- capacity for a post that did not exist inflates the denominator
    -- and makes utilisation look better than it was.
    where m.month_start >= date_trunc('month', s.start_date)
      and (s.end_date is null or m.month_start <= date_trunc('month', s.end_date))
)

select
    staff_id,
    cost_centre_id,
    role,
    month_start,
    contract_hours_week,
    fte_share,
    round(contract_hours_week * {{ weeks_per_month }} * (1 - {{ absence_allowance }}), 2)
        as capacity_hours
from matched
