-- Source: notebook Q5 "Promotions" (cell 29) -> q5_promo.csv

select
    promo_label,
    avg(sales)              as sales_per_day,
    avg(customers)          as customers_per_day,
    avg(sales_per_customer) as sales_per_customer
from {{ ref('int_rossmann__analysis_scope') }}
group by promo_label
