-- Source: notebook cell 9, `cust_nosales = int(((train["Customers"] > 0) & (train["Sales"] == 0)).sum())`

select *
from {{ ref('stg_rossmann__train') }}
where customers > 0
  and sales = 0
