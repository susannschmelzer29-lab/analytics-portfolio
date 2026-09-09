-- Source: notebook Q6 "Store Type Comparison" (cell 32) -> q6_storetype.csv

select
    store_type,
    avg(sales)                as sales_per_day,
    avg(customers)            as customers_per_day,
    avg(sales_per_customer)   as sales_per_customer,
    count(distinct store_id)  as stores
from {{ ref('int_rossmann__analysis_scope') }}
group by store_type
