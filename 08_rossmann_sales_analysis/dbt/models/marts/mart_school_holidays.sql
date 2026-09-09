-- Source: notebook Q4 school holiday split (cell 26) -> q4_school_holidays.csv

select
    case is_school_holiday when 0 then 'Normal' when 1 then 'School Holiday' end as school_holiday_label,
    avg(sales) as sales_per_day,
    count(*)   as days
from {{ ref('int_rossmann__analysis_scope') }}
group by is_school_holiday
