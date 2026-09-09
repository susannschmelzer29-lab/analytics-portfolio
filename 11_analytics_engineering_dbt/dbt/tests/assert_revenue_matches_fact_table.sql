-- Reconciliation test: the mart must not invent or lose money against
-- the fact table it is built from. Catches a wrong join or a lost filter
-- more reliably than any column-level test.

with from_fact as (
    select round(sum(billable_amount_eur), 2) as total
    from {{ ref('fct_service_delivery') }}
    where funding_source is not null
      and duration_hours > 0
),

from_mart as (
    select round(sum(revenue_eur), 2) as total
    from {{ ref('mart_funding_mix') }}
)

select
    f.total as fact_total,
    m.total as mart_total,
    abs(f.total - m.total) as difference
from from_fact f
cross join from_mart m
-- One cent of tolerance for rounding across the grouping levels.
where abs(f.total - m.total) > 0.01
