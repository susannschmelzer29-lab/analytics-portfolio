-- Source: notebook Q2, the per-store correlation printed to console
-- ("Correlation distance <-> sales: r = ..."). Not exported as a CSV in the
-- original pipeline, but a single SQL aggregate (DuckDB's corr()) -- worth
-- keeping as its own tiny mart instead of dropping it.

with per_store as (
    select
        store_id,
        avg(sales)              as sales_per_day,
        min(competition_distance) as competition_distance
    from {{ ref('int_rossmann__analysis_scope') }}
    group by store_id
)

select
    round(corr(sales_per_day, competition_distance), 3) as sales_vs_distance_corr
from per_store
