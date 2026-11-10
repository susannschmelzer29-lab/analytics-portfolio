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

**Stack:** Python · PyYAML · pytest · GitHub Actions (tests only) ·
Claude desktop app (scheduled local run)

```bash
pip install -e ".[dev]"
python -m pytest                          # 60 tests, offline, fictional data
python -m careerpipe validate             # how much of the profile is confirmed
python -m careerpipe build                # CV + LinkedIn texts, checked twice
python -m careerpipe compare --linkedin-text pasted.txt
```

The commands read from a private folder: `--home DIR`, else the environment
variable `CAREERPIPE_HOME`, else `~/.career-pipeline/`. That folder
holds the real profile and the private config, and it never enters the
repository.

---

## Status

| Step | What | State |
|---|---|---|
| 1 | Profile, German CV and LinkedIn texts, grounding check, leak test | **built**, 60 tests |
| 2 | Job research (Jobsuche API of the Bundesagentur für Arbeit) | planned |
| 3 | Profile bottleneck and market bottleneck | planned |
| 4 | Recommendation: certificate *or* project, side by side | planned |
| 5 | Learning loop, with supervised learning against a rule baseline | planned |

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

## Why it runs locally, not in CI

The weekly research is meant to run as a **scheduled task in the Claude
desktop app** on the owner's machine. GitHub Actions runs only the tests,
on fictional data. The pipeline itself never runs in CI: the repository is
public, and its logs would expose the private filters.

## No pile-up

The research runs every week, so it must not fill the disk:

* outputs have fixed names and are overwritten in place (tested: two runs leave
  the same files);
* raw ads are pruned after a set number of weeks, and only the counts are kept
  (planned, step 2–3);
* the report is capped at ten matches and one recommendation.

## Limitations

* The CV is Markdown for now. The PDF is still open.
* The grounding check knows the skills in its vocabulary. A skill the list
  does not contain is not checked. The list is meant to grow.
* Numbers are checked; free-text claims ("led a team of …") are not. That
  needs either a stricter template or a model-based check with its own
  evaluation, as in [project 12](../12_llm_evaluation_harness/).
* Steps 2–5 are planned, not built. The supervised-learning part will start
  with dozens of ratings, not thousands, so its models stay simple and
  explainable.

## Related

* [10 · Agent Engineering Lab](../10_agent_engineering_lab/): the canary and
  the read-only raw data come from here.
* [12 · LLM Evaluation Harness](../12_llm_evaluation_harness/): the
  "a check must be able to fail" rule.
* [13 · Pflegeleistungen-RAG](../13_pflegeleistungen_rag/): the same
  "cite or refuse" stance, applied to a CV.
