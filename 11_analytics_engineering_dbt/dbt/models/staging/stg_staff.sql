with source as (
    select * from {{ ref('raw_staff') }}
),

renamed as (
    select
        staff_id,
        trim(role)                                            as role,
        cost_centre_id,
        cast(contract_hours_week as decimal(4,1))             as contract_hours_week,
        cast(start_date as date)                              as start_date,
        nullif(trim(cast(end_date as varchar)), '')::date     as end_date,

        -- Derived here because it is a pure restatement of the source,
        -- not a business rule: the share of a full-time post.
        round(
            cast(contract_hours_week as decimal(4,1))
            / {{ var('full_time_hours_week') }}, 3
        )                                                     as fte_share
    from source
)

select * from renamed
