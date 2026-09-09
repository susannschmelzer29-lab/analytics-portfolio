-- Source: notebook function clean_store() in cell 12.
-- Missing CompetitionDistance -> 2x the observed max (or 99,999 if the whole
-- column is null); missing Promo2/Competition date parts -> 0; CompetitionProximity
-- buckets match the original pd.cut(bins=[0,500,1500,5000,inf]) exactly.

with distance_bounds as (
    select max(competition_distance) as max_distance
    from {{ ref('stg_rossmann__store') }}
),

filled as (
    select
        s.store_id,
        s.store_type,
        s.assortment_code,
        coalesce(s.competition_distance, db.max_distance * 2, 99999) as competition_distance,
        coalesce(s.competition_open_since_month, 0) as competition_open_since_month,
        coalesce(s.competition_open_since_year, 0)  as competition_open_since_year,
        s.is_promo2,
        coalesce(s.promo2_since_week, 0) as promo2_since_week,
        coalesce(s.promo2_since_year, 0) as promo2_since_year,
        s.promo_interval
    from {{ ref('stg_rossmann__store') }} s
    cross join distance_bounds db
)

select
    *,
    case assortment_code
        when 'a' then 'Basic' when 'b' then 'Extra' when 'c' then 'Extended'
        else assortment_code
    end as assortment_label,
    case
        when competition_distance <= 500 then '<500m'
        when competition_distance <= 1500 then '500-1500m'
        when competition_distance <= 5000 then '1.5-5km'
        else '>5km'
    end as competition_proximity
from filled
