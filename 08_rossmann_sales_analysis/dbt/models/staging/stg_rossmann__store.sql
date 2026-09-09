-- Source: notebook cell "## 1 · Load Data" (raw["store"]) — typing/renaming only.

with source as (
    select * from {{ ref('raw_store_sample') }}
)

select
    "Store"::integer                       as store_id,
    "StoreType"::varchar                   as store_type,
    "Assortment"::varchar                  as assortment_code,
    "CompetitionDistance"::double          as competition_distance,
    "CompetitionOpenSinceMonth"::integer   as competition_open_since_month,
    "CompetitionOpenSinceYear"::integer    as competition_open_since_year,
    "Promo2"::integer                      as is_promo2,
    "Promo2SinceWeek"::integer             as promo2_since_week,
    "Promo2SinceYear"::integer             as promo2_since_year,
    nullif("PromoInterval"::varchar, '')   as promo_interval
from source
