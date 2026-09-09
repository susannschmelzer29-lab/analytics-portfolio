-- Delivered hours against available capacity, per cost centre and month.
-- The question this answers: are we staffed for what we actually deliver?

with delivered as (
    select
        cost_centre_id,
        month_start,
        sum(duration_hours)                                     as delivered_hours,
        sum(case when is_billable then duration_hours else 0 end) as billable_hours,
        sum(billable_amount_eur)                                as billable_amount_eur,
        count(*)                                                as service_count
    from {{ ref('fct_service_delivery') }}
    -- Rows with a broken reference have no cost centre and would land in
    -- a NULL bucket. They are reported by the tests, not silently mixed
    -- into a real cost centre's figures.
    where cost_centre_id is not null
      and duration_hours > 0
    group by 1, 2
),

capacity as (
    select
        cost_centre_id,
        month_start,
        sum(capacity_hours)     as capacity_hours,
        sum(fte_share)          as fte
    from {{ ref('int_staff_capacity_monthly') }}
    group by 1, 2
),

centres as (
    select * from {{ ref('stg_cost_centres') }}
)

select
    c.cost_centre_id,
    ce.cost_centre_name,
    ce.funding_source,
    c.month_start,

    c.capacity_hours,
    c.fte,
    coalesce(d.delivered_hours, 0)      as delivered_hours,
    coalesce(d.billable_hours, 0)       as billable_hours,
    coalesce(d.billable_amount_eur, 0)  as billable_amount_eur,
    coalesce(d.service_count, 0)        as service_count,

    -- Utilisation: delivered against available. Above 1.0 means the team
    -- delivered more than its contracted capacity -- which is a finding,
    -- not an error, and the reason the sanity test allows up to 2.0.
    case
        when c.capacity_hours > 0
            then round(coalesce(d.delivered_hours, 0) / c.capacity_hours, 3)
    end                                 as utilisation_rate,

    case
        when coalesce(d.delivered_hours, 0) > 0
            then round(coalesce(d.billable_hours, 0) / d.delivered_hours, 3)
    end                                 as billable_share

from capacity c
left join delivered d
    on c.cost_centre_id = d.cost_centre_id
   and c.month_start    = d.month_start
left join centres ce
    on c.cost_centre_id = ce.cost_centre_id
