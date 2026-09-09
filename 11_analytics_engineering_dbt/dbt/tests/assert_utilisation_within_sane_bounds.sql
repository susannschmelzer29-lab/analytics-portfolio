-- Utilisation above 2.0 is not a finding, it is arithmetic gone wrong:
-- a team cannot deliver twice its contracted capacity for a whole month.
-- Between 1.0 and 2.0 is allowed on purpose -- overtime is real.

select
    cost_centre_id,
    month_start,
    delivered_hours,
    capacity_hours,
    utilisation_rate
from {{ ref('mart_utilisation_monthly') }}
where utilisation_rate is not null
  and (utilisation_rate < 0 or utilisation_rate > 2.0)
