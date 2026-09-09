-- Source: notebook Q5 promo x store type pivot (cell 29) -> q5_promo_by_storetype.csv
-- pivot_table(index=StoreType, columns=Promo_lbl) becomes conditional aggregation.

select
    store_type,
    avg(case when promo_label = 'No Promo' then sales end)   as no_promo_sales_per_day,
    avg(case when promo_label = 'With Promo' then sales end) as with_promo_sales_per_day,
    round(
        (
            avg(case when promo_label = 'With Promo' then sales end)
            / avg(case when promo_label = 'No Promo' then sales end) - 1
        ) * 100, 1
    ) as uplift_pct
from {{ ref('int_rossmann__analysis_scope') }}
group by store_type
