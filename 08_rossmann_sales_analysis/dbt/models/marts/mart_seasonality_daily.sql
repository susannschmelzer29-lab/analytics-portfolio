-- Source: notebook Q3 "Seasonality" (cell 23) -> q3_seasonality_daily.csv
-- Chain-wide daily aggregate for the dashboard's time-series view.

select
    sale_date,
    sale_year,
    year_month,
    sum(sales)                as total_sales,
    sum(customers)            as total_customers,
    count(distinct store_id)  as open_stores
from {{ ref('int_rossmann__analysis_scope') }}
group by sale_date, sale_year, year_month
order by sale_date
