-- Source: notebook Q6 store type x assortment pivot (cell 32) -> q6_storetype_x_assortment.csv

select
    store_type,
    avg(case when assortment_label = 'Basic' then sales end)    as basic,
    avg(case when assortment_label = 'Extra' then sales end)    as extra,
    avg(case when assortment_label = 'Extended' then sales end) as extended
from {{ ref('int_rossmann__analysis_scope') }}
group by store_type
