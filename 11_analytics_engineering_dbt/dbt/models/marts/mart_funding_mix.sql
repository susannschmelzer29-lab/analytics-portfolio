-- Where the money comes from, and how much unfunded work sits behind it.
--
-- The interesting column is unbillable_hours: work that is real, necessary
-- and has no funder. In a social-services provider that number is the
-- argument in every budget negotiation.

with f as (
    select * from {{ ref('fct_service_delivery') }}
    where funding_source is not null
      and duration_hours > 0
)

select
    funding_source,
    date_trunc('quarter', service_date)::date            as quarter_start,

    count(distinct client_id)                            as clients_served,
    count(*)                                             as service_count,
    round(sum(duration_hours), 1)                        as total_hours,
    round(sum(case when is_billable then duration_hours else 0 end), 1)
                                                         as billable_hours,
    round(sum(case when is_billable then 0 else duration_hours end), 1)
                                                         as unbillable_hours,
    round(sum(billable_amount_eur), 2)                   as revenue_eur,

    round(
        sum(case when is_billable then 0 else duration_hours end)
        / nullif(sum(duration_hours), 0), 3
    )                                                    as unbillable_share

from f
group by 1, 2
