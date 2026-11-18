# 14 · Career Pipeline

[![14 career pipeline](https://github.com/susannschmelzer29-lab/analytics-portfolio/actions/workflows/career_pipeline.yml/badge.svg)](https://github.com/susannschmelzer29-lab/analytics-portfolio/actions/workflows/career_pipeline.yml)

A pipeline that keeps a CV and LinkedIn texts in step with this portfolio,
researches the job market on a schedule, and measures two bottlenecks: the
gap in the owner's profile and the gap in the market. **It recommends; it never
decides.** Every next step is the owner's choice.

The interesting part is not the text generation. Two things matter:
**no generated sentence may claim more than the profile holds**, and **the
owner's private search criteria must never reach a public text**. Both are
enforced in code, with a test that proves each check can still fail.

**Stack:** Python · PyYAML · scikit-learn · pytest · Jobsuche API of the
Bundesagentur für Arbeit · Apify actors · GitHub Actions (tests only) ·
Claude desktop app (scheduled local run)

```bash
pip install -e ".[dev]"
python -m pytest                          # 133 tests, offline, fictional data
python -m careerpipe validate             # how much of the profile is confirmed
python -m careerpipe build                # CV (Markdown, HTML, PDF) + LinkedIn texts, checked twice
python -m careerpipe compare --linkedin-text pasted.txt
python -m careerpipe research             # job research, bottlenecks, recommendation, learning loop
```

The commands read from a private folder: `--home DIR`, else the environment
variable `CAREERPIPE_HOME`, else `~/.career-pipeline/`. That folder
holds the real profile and the private config, and it never enters the
repository.

---

## Status

| Step | What | State |
|---|---|---|
| 1 | Profile, German CV and LinkedIn texts, grounding check, leak test | **built** |
| 2 | Job research: Arbeitsagentur API plus job boards via Apify, work model, match score | **built** |
| 3 | Profile bottleneck and market bottleneck, pooled over runs | **built**, needs weeks of data |
| 4 | Recommendation: certificate *or* project, side by side | **built**, waits for a stable gap |
| 5 | Learning loop, with supervised learning against a rule baseline | **built**, waits for 20 ratings |

All 133 tests run offline on fictional data. Steps 3–5 are built and tested,
but they only say something once real weeks of data and ratings exist; until
then the report says so instead of guessing.

The full scope and the acceptance criteria are in [PLAN.md](PLAN.md).

## How step 1 works

```
private folder                                repository (public)
  profile.yaml   ── confirmed entries ──►      careerpipe
  config.yaml    ── private terms ─────►         render     German CV + LinkedIn texts
  application                                     grounding  every skill and number traced back
  folder (read-only)                              leak       private terms, canary first
                                                       │
                                     all checks pass?  ├─ no  → nothing is written
                                                       └─ yes → private folder/out/
```

## How steps 2–5 work

```
sources (one interface)        per ad                         per run, pooled over the kept weeks
  Arbeitsagentur API  ──┐      work model: 4 classes + reason   profile bottleneck ─┐
  job boards (Apify)  ──┴──►   match: known skills, met/missing  market bottleneck  ─┴─► overlap
                               wishes from the private config     history (one row per run)
                                     │                                    │
                     clear ──► report (top 10)              stable 3 runs? ─► recommendation
                     unclear ─► set-aside list                learning goal set? ─► brake
                                     │
                     owner rates ads ─► learning loop: rule vs. two models (cross-validated)
                                        proposals only; owner switches on; regression check
```

Everything is counted in code. No language model decides a score, a gap or a
recommendation.

## The five decisions worth explaining

### 1. Two worlds, separated by a file boundary

The real profile, the search filters, the contact details and the path to the
application folder live in a private folder outside the repository. It may
sit inside the application folder: it is then the only place there the
pipeline writes to, and it is skipped whenever the folder is read. The repository holds the
code and a **fictional** test person. While building step 1 the leak scan
found that the test fixtures had used real filter words and a real company
name. They looked harmless, being test data, but anyone reading the public
repository could have inferred the search from them. The fixtures now use
neutral terms that have nothing to do with the owner.

### 2. Drafts are allowed; unconfirmed facts are not

Every profile entry carries an explicit `confirmed` flag. The first profile was
drafted automatically from an existing CV and a skills review, so nothing in
it was confirmed. Only confirmed entries reach a text, and nothing is generated
until the person and summary blocks are confirmed. A draft can sit in the
file without ever leaking into a CV.

### 3. The grounding check: the model words, it never adds

Templates generate the texts today; a language model may reword them later.
Either way, the check runs in code:

* every **skill term** in a text (from a vocabulary that deliberately includes
  the tempting ones: Power BI, AWS, Snowflake …) must occur in the confirmed
  profile, aliases included;
* every **number** must occur in the confirmed profile, or in a source handed
  in on purpose, such as the contact block of the CV.

A test replaces the renderer with one that adds "Power BI" or "15 Jahre", and
the run must stop. One bug surfaced here: the fictional profile has a date
`2011-10`, and its month made "10 Jahre" look grounded. Dates now count only
as whole tokens (`10/2011`), and a regression test keeps it that way.

### 4. The leak test fails loudly, never silently

Private terms are matched at the **start of a word, open at the end**. The
first version matched whole words only and would have let German compounds
through: a filter word inside a longer compound slipped past. A false alarm
stops the run and gets fixed in a minute; a missed compound would leak
without anyone noticing. Before any output is checked, a **canary** plants
every private term once. If one is not caught, the run stops, because a leak
test that cannot fail proves nothing (the same idea as the canary in
[project 10](../10_agent_engineering_lab/)).

A term can be private in one place and public in another, for example an
organisation that belongs in the CV. Such terms go on an explicit
`public_terms` list. The matcher never guesses exceptions.

### 5. Pinning is a choice, not a ranking

LinkedIn shows three pinned skills, and recruiters filter on exact skill
names. The first preview pinned "Schulung und Training", the skill with the
highest level. It is true, but it is the wrong filter for a data role. Pinning
is now an explicit `pin: true` in the profile (at most three). Transferable
skills rank after technical ones in every list.

## Four more decisions, from steps 2–5

### 6. Unclear is set aside, not dropped and not guessed

Most ads say nothing about where the work happens. The first live run put
191 of 295 checked ads into *unclear*. Guessing would hide that; dropping them
would lose real options. Two rules now split them into a separate list: ads
that mention home office without a share (worth a question to the employer),
and ads with no word about the place at all (usually on-site). The report
shows only their counts. A stated share always wins over the vague rule, and
each rule has its own test.

### 7. API first, scraping only by the owner's explicit choice

The Arbeitsagentur has a public API, and it is the first source. Three job
boards without an API run through Apify actors, because the owner chose that
on 2026-11-18; their terms still apply, and the decision is written down in
PLAN.md. Two public-sector portals were checked. One was left out: no data interface,
session-bound pages, so a scraper would break with every change. The state
career portal of Mecklenburg-Vorpommern, ministries included, is read
directly: plain pages, stable ad ids, and a robots.txt that allows it. Its
own part-time filter is not used, because ads marked "teilzeitfähig" would
drop out under it. One board
failing never stops the others; the report names it. The detail budget only
counts ads whose full text still has to be fetched: the first version capped
all ads and silently skipped 130 of 425.

### 8. Bottlenecks need time, and the report says so

The market bottleneck uses ads that stay online at least three weeks as a
proxy for "hard to fill". A search over the last 14 days cannot show that in
its first run, so the report states "not measurable yet" with the sample size
instead of a number. A recommendation appears only after the same gap has led
three runs in a row, and a learning goal in the private config pauses all new
recommendations. Effort and cost come from a catalog the owner checks; empty
fields read "bitte prüfen", never an invented figure.

### 9. The learning loop proposes; the owner switches on

The owner rates offered ads in a CSV next to the config. From 20 ratings on,
the rule is compared with a logistic regression and a decision tree under
cross-validation (precision, recall, confusion matrix). A model ranks only if
it beats the rule *and* the owner sets `use_model`, and even then a regression
check falls back to the rule if a known good match would drop out of the top
results. New search terms and switching off a quiet source are only proposed.
Every change of these settings is logged with its date and previous value.

## Why it runs locally, not in CI

The weekly research is meant to run as a **scheduled task in the Claude
desktop app** on the owner's machine. GitHub Actions runs only the tests,
on fictional data. The pipeline itself never runs in CI: the repository is
public, and its logs would expose the private filters.

## No pile-up

The research runs every week, so it must not fill the disk:

* outputs have fixed names and are overwritten in place (tested: two runs leave
  the same files);
* ad texts are not kept, except for ads offered for rating; every entry in the
  list of seen ads is pruned after a set number of weeks (default 8);
* the run history is one file with one row per run date;
* the report is capped at ten matches and one recommendation.

## Limitations

* The PDF is printed by a local Edge or Chrome. Without one, the HTML is written
  and can be printed by hand. The PDF adds no text of its own: it comes from the
  HTML whose visible text went through both checks.
* The grounding check knows the skills in its vocabulary. A skill the list
  does not contain is not checked. The list is meant to grow.
* Numbers are checked; free-text claims ("led a team of …") are not. That
  needs either a stricter template or a model-based check with its own
  evaluation, as in [project 12](../12_llm_evaluation_harness/).
* The match score counts skills from the vocabulary only. An ad that names
  none of them gets no score, and the report says so.
* Must-have and nice-to-have requirements are not told apart yet; every known
  skill in an ad counts the same.
* Part-time is detected from wording in the ad text, except where a source can
  filter for it itself.
* The learning loop starts with dozens of ratings, not thousands, so its models
  stay simple and explainable. A text classifier for the work model is
  compared against the rule, but it does not take over on its own.

## Related

* [10 · Agent Engineering Lab](../10_agent_engineering_lab/): the canary and
  the read-only raw data come from here.
* [12 · LLM Evaluation Harness](../12_llm_evaluation_harness/): the
  "a check must be able to fail" rule.
* [13 · Pflegeleistungen-RAG](../13_pflegeleistungen_rag/): the same
  "cite or refuse" stance, applied to a CV.
