-- Source: notebook "## 6 · Export the Analysis Master Table" (cell 37)
-- -> rossmann_master_tableau.csv. Full grain (incl. closed days), for BI
-- tools such as Tableau/Power BI to connect to directly.

select * from {{ ref('int_rossmann__master') }}
