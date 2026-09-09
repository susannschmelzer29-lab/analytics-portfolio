-- Source: notebook Q3 "Seasonality" (cell 23) -> q3_seasonality_weekday.csv

select
    weekday_name,
    weekday_sort,
    avg(sales)     as sales_per_day,
    avg(customers) as customers_per_day
from {{ ref('int_rossmann__analysis_scope') }}
group by weekday_name, weekday_sort
order by weekday_sort
