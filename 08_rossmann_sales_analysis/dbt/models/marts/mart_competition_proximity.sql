-- Source: notebook Q2 "Location Factors" (cell 20) -> q2_competition_distance.csv

select
    competition_proximity,
    avg(sales)                       as sales_per_day,
    avg(customers)                   as customers_per_day,
    count(distinct store_id)         as stores
from {{ ref('int_rossmann__analysis_scope') }}
group by competition_proximity
order by
    case competition_proximity
        when '<500m' then 1 when '500-1500m' then 2 when '1.5-5km' then 3 else 4
    end
