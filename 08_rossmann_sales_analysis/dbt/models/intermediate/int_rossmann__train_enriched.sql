-- Source: notebook function normalize_dates() + the Holiday_lbl/Promo_lbl
-- assignment in cell 13 ("## 3 · Cleaning, Date Normalization & Merge").
-- Kaggle's DayOfWeek (1=Mon..7=Sun) is used directly instead of re-deriving
-- it from the date — same source column the notebook computes dt.dayofweek
-- from, one fewer derivation.

select
    store_id,
    sale_date,
    day_of_week,
    case day_of_week
        when 1 then 'Mon' when 2 then 'Tue' when 3 then 'Wed' when 4 then 'Thu'
        when 5 then 'Fri' when 6 then 'Sat' when 7 then 'Sun'
    end                                         as weekday_name,
    day_of_week                                 as weekday_sort,
    day_of_week in (6, 7)                       as is_weekend,
    date_part('year', sale_date)::integer       as sale_year,
    date_part('month', sale_date)::integer      as sale_month,
    strftime(sale_date, '%B')                   as month_name,
    date_part('week', sale_date)::integer       as sale_week,
    date_part('quarter', sale_date)::integer    as sale_quarter,
    strftime(sale_date, '%Y-%m')                as year_month,
    sales,
    customers,
    is_open,
    is_promo,
    case is_promo when 1 then 'With Promo' else 'No Promo' end as promo_label,
    state_holiday_code,
    case state_holiday_code
        when '0' then 'No Holiday'
        when 'a' then 'Public Holiday'
        when 'b' then 'Easter'
        when 'c' then 'Christmas'
        else 'No Holiday'
    end                                          as holiday_label,
    is_school_holiday
from {{ ref('stg_rossmann__train') }}
