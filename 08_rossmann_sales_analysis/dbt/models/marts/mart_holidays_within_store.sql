-- Source: notebook Q4 selection-effect check (cell 26) -> q4_holidays_within_store.csv
-- Only stores that are ever open on a public holiday are counted -- isolates
-- the within-store effect from the fact that higher-performing stores are
-- more likely to open on holidays in the first place.

with holiday_stores as (
    select distinct store_id
    from {{ ref('int_rossmann__analysis_scope') }}
    where holiday_label != 'No Holiday'
),

same_store as (
    select *
    from {{ ref('int_rossmann__analysis_scope') }}
    where store_id in (select store_id from holiday_stores)
),

by_holiday as (
    select
        holiday_label,
        avg(sales) as sales_per_day,
        count(*)   as days
    from same_store
    group by holiday_label
),

baseline as (
    select sales_per_day as base_sales_per_day
    from by_holiday
    where holiday_label = 'No Holiday'
)

select
    b.holiday_label,
    b.sales_per_day,
    b.days,
    round((b.sales_per_day / baseline.base_sales_per_day - 1) * 100, 1) as uplift_pct
from by_holiday b
cross join baseline
