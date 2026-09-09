# The five planted defects

`scripts/generate_seeds.py` deliberately writes five broken rows into the
source data. Without them the test suite would prove nothing: a green run
over clean data is indistinguishable from a green run over no data at all.

Each defect has exactly one test that catches it.

| # | Defect | Where planted | Caught by | Severity |
|---|---|---|---|---|
| 1 | Exact duplicate of a service row | `raw_services` | removed in `stg_services`; `unique_fct_service_delivery_service_id` proves it worked | error |
| 2 | Service dated 14 days before the client's entry | `raw_services` | `assert_no_service_before_client_entry` | warn |
| 3 | Negative duration (−45 minutes) | `raw_services` | `assert_duration_is_positive` | warn |
| 4 | Orphan `staff_id` = `S999` | `raw_services` | `relationships … staff_id` | warn |
| 5 | Unknown `service_type_code` = `XXX` | `raw_services` | `relationships … service_type_code` | warn |

Expected result of `dbt build`: **57 pass, 4 warn, 0 error.**

Defect 1 produces no warning on purpose — it is removed in staging,
because a row delivered twice by the transport layer is not a fact about
the world. The uniqueness test on the fact table is what proves the
removal happened.

## Why the counts matter, not just the pass/fail

An early version of the generator ignored client entry and exit dates.
Defect 2's test then fired 1,496 times instead of once. The build was
still "green with warnings", and the signal was gone.

So the check is not *does the test warn* but *does it warn exactly as
often as expected*. If `assert_no_service_before_client_entry` ever
reports more than 1, something changed — either in the generator or in a
model — and it needs looking at.

## Adding a rule

New test → new planted defect. A rule with nothing to catch is untested,
and an untested rule is a comment.
