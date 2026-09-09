-- Staging: rename, cast, no business logic.
-- Rule for this layer: one model per source, no joins, no aggregation.
-- If a join appears here, the layering has been broken.

with source as (
    select * from {{ ref('raw_clients') }}
),

renamed as (
    select
        client_id,
        cast(entry_date as date)                              as entry_date,
        -- Empty string means "still with us", not "unknown".
        nullif(trim(cast(exit_date as varchar)), '')::date    as exit_date,
        cast(care_level as integer)                           as care_level,
        trim(district)                                        as district
    from source
)

select * from renamed
