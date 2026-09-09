-- Source: notebook cell 9, `neg_sales = int((train["Sales"] < 0).sum())`
-- A dbt test passes when the query returns zero rows.

select *
from {{ ref('stg_rossmann__train') }}
where sales < 0
