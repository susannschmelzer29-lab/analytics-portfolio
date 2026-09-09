-- Source: notebook Q1 "Store Ranking" (cell 17) -> q1_store_ranking.csv

with by_store as (
    select
        store_id,
        sum(sales)                    as total_sales,
        avg(sales)                    as sales_per_day,
        avg(customers)                as customers_per_day,
        avg(sales_per_customer)       as sales_per_customer,
        count(*)                      as days_open,
        min(store_type)               as store_type,
        min(assortment_label)         as assortment,
        min(competition_proximity)    as competition_proximity
    from {{ ref('int_rossmann__analysis_scope') }}
    group by store_id
)

select
    *,
    rank() over (order by sales_per_day desc)                        as sales_rank,
    round(percent_rank() over (order by sales_per_day) * 100, 1)     as sales_percentile
from by_store
order by sales_per_day desc
