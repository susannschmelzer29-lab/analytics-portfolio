-- Source: notebook Q4 "Holidays" naive comparison (cell 26) -> q4_holidays.csv
-- Naive = across all stores, no selection-effect correction.
-- See mart_holidays_within_store for the corrected version.

with by_holiday as (
    select
        holiday_label,
        avg(sales) as sales_per_day,
        count(*)   as days
    from {{ ref('int_rossmann__analysis_scope') }}
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
