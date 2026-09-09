-- Source: notebook cell 13 (merge train_n + store_n) — the "master" table.
-- CompetitionActive / Promo2Active reproduce the date-comparison logic;
-- weather/trends merges are dropped (optional sources not present in this repo).

with train as (
    select * from {{ ref('int_rossmann__train_enriched') }}
),

store as (
    select * from {{ ref('int_rossmann__store_cleaned') }}
)

select
    t.store_id,
    t.sale_date,
    t.day_of_week,
    t.weekday_name,
    t.weekday_sort,
    t.is_weekend,
    t.sale_year,
    t.sale_month,
    t.month_name,
    t.sale_week,
    t.sale_quarter,
    t.year_month,
    t.sales,
    t.customers,
    t.is_open,
    t.is_promo,
    t.promo_label,
    t.state_holiday_code,
    t.holiday_label,
    t.is_school_holiday,
    s.store_type,
    s.assortment_code,
    s.assortment_label,
    s.competition_distance,
    s.competition_proximity,
    s.is_promo2,
    s.promo_interval,
    case
        when s.competition_open_since_year > 0 and s.competition_open_since_month > 0
            then make_date(s.competition_open_since_year, s.competition_open_since_month, 1) <= t.sale_date
        else false
    end as competition_active,
    coalesce(
        s.is_promo2 = 1
        and (
            t.sale_year > s.promo2_since_year
            or (t.sale_year = s.promo2_since_year and t.sale_week >= s.promo2_since_week)
        ),
        false
    ) as promo2_active,
    case when t.customers > 0 then t.sales::double / t.customers else null end as sales_per_customer
from train t
left join store s on t.store_id = s.store_id
