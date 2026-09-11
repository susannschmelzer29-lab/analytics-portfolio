# 10 · Agent Engineering Lab

[![10 agent lab](https://github.com/susannschmelzer29-lab/analytics-portfolio/actions/workflows/agent_lab.yml/badge.svg)](https://github.com/susannschmelzer29-lab/analytics-portfolio/actions/workflows/agent_lab.yml)


A data-checking pipeline where the **guardrails are visible in the file
tree**.

Projects 01–09 in this portfolio show that an analysis can be computed.
This one shows something different: that an agent can be bounded, secured
and made verifiable. The pipeline is the occasion; the boundaries are the
subject.

**Stack:** Python (pandas) · pytest · Docker · GitHub Actions

```bash
pip install -e ".[dev]"
python -m pytest                                              # 51 tests
python -m agentlab.pipeline --input data/raw --key case_id --docs docs
```

No API key needed. Deliberately: a portfolio project you cannot start is
not a portfolio project.

---

## The six decisions worth explaining

### 1. Raw data is immutable — enforced three times

`data/raw/` is never written to. Not because a document says so, but
because three independent layers prevent it:

| Layer | Where | Effect |
|---|---|---|
| Rule | `CLAUDE.md` | The agent knows |
| Permission | `.claude/settings.json`, `deny` | Applies in **every** mode |
| Program | `.claude/hooks/guard.sh` | Inspects the actual command |

The middle layer is the decisive one: a `deny` rule holds even in the most
permissive permission mode. A sentence in a prompt is a request to a
language model; a rule is a law.

A fourth layer in the container: `data/raw` is mounted read-only.

### 2. The canary — who checks the checker?

An unattended pipeline can write plausible and wrong reports for months.
*"All files checked, no anomalies"* is exactly the output you also get
when the check never ran.

`src/agentlab/canary.py` therefore holds a file with five **deliberate**
defects:

| Code | Planted defect |
|---|---|
| `MISSING_RED` | column `note` 50 % empty |
| `MISSING_AMBER` | column `quantity` 10 % empty |
| `DUPLICATES` | `case_id` 1003 appears twice |
| `TYPE_MISMATCH` | `amount` contains `1.2O0` — letter O, not zero |
| `CONSTANT` | `tenant` is `A` throughout |

It runs in **every** pass. If the checks do not find all five, the
pipeline aborts and discards the results — for the whole run, not just
that file.

```python
passed, missing = verify_canary()
if not passed:
    raise CanaryError(...)     # run void
```

### 3. Whatever reaches outside is handed in

`checks.py` knows nothing of filesystem, network or model. File access
(`reader`), the model call (`narrator`) and the knowledge lookup
(`knowledge`) are parameters:

```python
run(paths)                          # findings, no model, no network
run(paths, narrator=my_agent)       # plus a prose summary
run(paths, knowledge=DocsKnowledge("docs"))   # plus explanations
```

Three consequences: tests run offline in under a second, the repository
works without credentials, and the model call is swappable rather than
welded into the code.

### 4. Retrieval is data, never instruction

The knowledge lookup answers *"is `note` mandatory?"* from the project's
own documentation — keyword retrieval over `docs/*.md`, no embeddings, no
network.

Retrieved passages go into the **report**, as quotations with a source.
They never enter a system prompt and never influence a tool decision.

That is not caution for its own sake. A language model cannot reliably
separate your instruction from a text it has read — both are one token
stream. Whoever can write into an indexed document would otherwise steer
the agent. OWASP maps that finding onto six of the ten categories in its
2026 top ten for agentic applications.

`_sanitise()` additionally strips instruction-shaped lines and truncates
to 400 characters. That is a second layer and explicitly **not** a
guarantee — the real boundary is architectural.

An answer without evidence is never `grounded`. An unsourced retrieval
result is a claim, not knowledge.

### 5. The agent runs in a container

`Dockerfile` is the build and test environment. `Dockerfile.agent` is
where **the agent itself** runs — Node plus the Claude Code CLI, as user
`agent`, not root.

```bash
docker compose run --rm lab                  # tests, no network at all
docker compose run --rm agent                # Claude Code in the container
./run_agent_container.sh "check data/raw"    # one task, then exit
```

The container is the outer boundary, not the only one: the `deny` rules
still apply inside it. That combination is what makes
`--dangerously-skip-permissions` defensible in here and reckless on a
working machine.

### 6. The checks repair nothing

No function fills missing values, removes duplicates or coerces types.
They report. An automation that silently corrects turns a visible data
error into an invisible one.

---

## Three bugs this project found in itself

Worth recording, because they are the normal case and because a
repository that only shows the finished state teaches nothing.

**Retrieval scored a confident 0.5 on "What is the capital of Peru?"**
Plain word overlap counted *what* and *the* as matches. Fixed with IDF
weighting — a term appearing in most sections carries almost no weight.

**IDF then went negative.** `log(n / (1 + df))` is below zero for a term
in nearly every section, and a negative weight inverts the ratio. Clamped
at zero.

**And it still failed, because eleven sections are not enough for IDF to
learn that "what" is a question word.** Fixed with an explicit stopword
list — the honest fix for a small corpus, encoding knowledge the data is
too small to supply.

Separately: the knowledge lookup originally asked about the *file* rather
than the *column*, so every question was too generic to retrieve anything.
`Finding` gained a `column` field.

## Layout

```
├── CLAUDE.md               project rules — under 60 lines, always in context
├── PLAN.md                 current assignment with acceptance criteria
├── .claude/
│   ├── settings.json       permissions: deny / ask / allow
│   ├── hooks/guard.sh      gatekeeper before every Bash call
│   ├── hooks/after_change.sh   tests after every file change
│   ├── skills/datacheck/   the instruction, with boundaries and a self-check
│   └── agents/source-finder.md   subagent: read-only, small model
├── src/agentlab/
│   ├── models.py           dataclasses, no behaviour
│   ├── checks.py           the rules — pure, testable, no outside world
│   ├── canary.py           the file with the known defects
│   ├── knowledge.py        retrieval over docs/, with the injection boundary
│   └── pipeline.py         orchestration, aborts on canary failure
├── docs/                   data dictionary and rules — also the retrieval corpus
├── tests/                  51 tests, offline, under a second
├── Dockerfile              build and test
├── Dockerfile.agent        the agent's own container
├── docker-compose.yml      lab (no network) and agent
├── data/raw/               immutable (deny rule + hook + read-only mount)
├── data/processed/         generated, reproducible at any time
└── reports/                results for humans
```

## Why `raw` and `processed` are separate

The most important line in the tree. Raw data is never overwritten — then
**every** processing error is repairable, because the input still exists.
Everything under `processed/` may be deleted at any time; it is rebuilt
from `raw/`.

## Adding the model

Without a key everything runs except the prose summary. With one:

```bash
cp .env.example .env        # ANTHROPIC_API_KEY, .env is gitignored
./run_pipeline.sh data/raw
```

`run_pipeline.sh` shows the pattern that matters:

* `--permission-mode dontAsk` — anything not explicitly allowed is denied
  rather than queried. In an unattended run there is nobody to answer.
* `--max-turns`, `--max-budget-usd` — an agent that goes in circles costs
  a bounded amount.
* **`jq` before the model.** Collapsing the individual findings costs zero
  tokens; the model only sees the flagged files.

## Limitations

* The checking rules are deliberately simple. Ranges, referential
  integrity and time-series checks are missing.
* The canary covers exactly the five implemented rules. A new rule means a
  new planted defect, otherwise a blind spot grows.
* `guard.sh` matches command text. That catches accidents, not a
  determined attacker. The load-bearing boundary is the container.
* Retrieval is keyword-based. Good enough for a handful of documents and
  explainable to a stakeholder; it would not scale to thousands.

## Related

* [11 · Analytics Engineering](../11_analytics_engineering_dbt/) — the
  same data-quality thinking as a dbt test suite.
* [12 · LLM Evaluation Harness](../12_llm_evaluation_harness/) — proving
  the narrator in this project stays reliable.
