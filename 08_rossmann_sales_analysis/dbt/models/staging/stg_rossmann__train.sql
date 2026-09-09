-- Source: 08_rossmann_sales_analysis notebook, cell "## 1 · Load Data" (raw["train"])
-- Just typing/renaming here — no business logic yet. Mirrors dtype={"StateHoliday": "str"}
-- from the original pd.read_csv call.

with source as (
    select * from {{ ref('raw_train_sample') }}
)

select
    "Store"::integer          as store_id,
    "DayOfWeek"::integer       as day_of_week,
    "Date"::date               as sale_date,
    "Sales"::integer           as sales,
    "Customers"::integer       as customers,
    "Open"::integer            as is_open,
    "Promo"::integer           as is_promo,
    coalesce(nullif("StateHoliday"::varchar, ''), '0') as state_holiday_code,
    "SchoolHoliday"::integer   as is_school_holiday
from source
