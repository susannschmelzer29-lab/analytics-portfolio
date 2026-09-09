-- Source: notebook cell 9, `dup_train = train.duplicated(subset=["Store", "Date"]).sum()`
-- (a composite-key uniqueness test, done as a singular test rather than a
-- generic one since it spans two columns)

select store_id, sale_date, count(*) as n_rows
from {{ ref('stg_rossmann__train') }}
group by store_id, sale_date
having count(*) > 1
