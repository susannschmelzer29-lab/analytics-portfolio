-- Source: notebook Q3 "Seasonality" (cell 23) -> q3_seasonality_month.csv

select
    sale_month,
    avg(sales) as sales_per_day
from {{ ref('int_rossmann__analysis_scope') }}
group by sale_month
order by sale_month
