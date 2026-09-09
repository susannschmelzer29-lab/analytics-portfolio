-- Source: notebook cell 15 ("### Analysis Scope") — the `frame` table.
-- All six business-question marts (Q1-Q6) and the KPI cockpit are built on
-- top of this: closed days and zero-sales rows are noise for those questions,
-- but int_rossmann__master keeps them (e.g. for the Open Rate KPI).

select *
from {{ ref('int_rossmann__master') }}
where is_open = 1
  and sales > 0
