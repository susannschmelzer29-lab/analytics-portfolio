-- Source: notebook cell 9, `sales_closed = int(((train["Open"] == 0) & (train["Sales"] > 0)).sum())`

select *
from {{ ref('stg_rossmann__train') }}
where is_open = 0
  and sales > 0
