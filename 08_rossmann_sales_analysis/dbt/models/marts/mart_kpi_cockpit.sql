-- Source: notebook "## 5 · Management KPI Cockpit" (cell 35) -> kpi_management.csv
-- Open Rate uses the *unfiltered* master table (it needs closed days too);
-- every other KPI uses the analysis scope, exactly like the notebook.

with store_perf as (
    select store_id, sales_per_day from {{ ref('mart_store_performance') }}
),

quantiles as (
    select
        quantile_cont(sales_per_day, 0.9) as q90,
        quantile_cont(sales_per_day, 0.1) as q10
    from store_perf
),

decile_avgs as (
    select
        avg(case when sp.sales_per_day >= q.q90 then sp.sales_per_day end) as top_decile_avg,
        avg(case when sp.sales_per_day <= q.q10 then sp.sales_per_day end) as bottom_decile_avg
    from store_perf sp
    cross join quantiles q
),

promo as (
    select
        max(case when promo_label = 'With Promo' then sales_per_day end) as with_promo,
        max(case when promo_label = 'No Promo' then sales_per_day end)   as no_promo
    from {{ ref('mart_promo') }}
),

scope as (
    select
        round(sum(sales) / 1e6, 1)          as total_sales_eur_million,
        round(avg(sales), 0)                as avg_daily_sales_per_store,
        round(avg(customers), 0)            as avg_customers_per_store_day,
        round(avg(sales_per_customer), 2)   as avg_sales_per_customer,
        count(distinct store_id)            as number_of_stores
    from {{ ref('int_rossmann__analysis_scope') }}
),

open_rate as (
    select round(avg(is_open) * 100, 1) as open_rate_pct
    from {{ ref('int_rossmann__master') }}
)

select
    scope.total_sales_eur_million,
    scope.avg_daily_sales_per_store,
    scope.avg_customers_per_store_day,
    scope.avg_sales_per_customer,
    open_rate.open_rate_pct,
    round((promo.with_promo / promo.no_promo - 1) * 100, 1)                     as promo_uplift_pct,
    round(decile_avgs.top_decile_avg / decile_avgs.bottom_decile_avg, 1)        as sales_range_top_bottom_decile_factor,
    scope.number_of_stores
from scope
cross join open_rate
cross join promo
cross join decile_avgs
