-- Intermediate: the joins live here, so marts stay readable.
-- Ephemeral -- this is a step in the reasoning, not an artefact anyone
-- should query directly.

with services as (
    select * from {{ ref('stg_services') }}
),

types as (
    select * from {{ ref('stg_service_types') }}
),

staff as (
    select * from {{ ref('stg_staff') }}
),

centres as (
    select * from {{ ref('stg_cost_centres') }}
),

joined as (
    select
        s.service_id,
        s.client_id,
        s.staff_id,
        s.service_date,
        s.service_type_code,
        s.duration_minutes,
        s.duration_hours,

        t.service_type_name,
        t.is_billable,
        t.rate_per_hour_eur,

        st.role                 as staff_role,
        st.cost_centre_id,
        st.fte_share,

        cc.cost_centre_name,
        cc.funding_source,

        -- Left joins on purpose: an orphan key must survive into the
        -- fact table so the relationship test can fail on it. An inner
        -- join here would hide exactly the defect we want to find.
        case
            when st.staff_id is null then true
            when t.service_type_code is null then true
            else false
        end                     as has_orphan_reference
    from services s
    left join types    t  on s.service_type_code = t.service_type_code
    left join staff    st on s.staff_id          = st.staff_id
    left join centres  cc on st.cost_centre_id   = cc.cost_centre_id
),

costed as (
    select
        *,
        -- Only billable types produce revenue. A non-billable hour is
        -- real work, it just has no funder -- that distinction is the
        -- whole point of the funding-mix mart.
        case
            when is_billable and duration_hours > 0
                then round(duration_hours * rate_per_hour_eur, 2)
            else 0.00
        end as billable_amount_eur
    from joined
)

select * from costed
