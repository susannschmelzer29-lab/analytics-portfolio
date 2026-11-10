# Current assignment

## Goal
A career pipeline that keeps the public profile in step with the portfolio,
researches the job market on a schedule, and measures two bottlenecks. It
recommends, it never decides: every next step is the owner's choice.

## Principle: two separate worlds

| | Public | Private |
|---|---|---|
| Content | projects, certificates, skills, experience | search filters, search fields, schedule |
| Outputs | CV, LinkedIn text suggestions, README sections | job list, bottleneck analysis, recommendations |
| Location | this repository | outside the repository (`~/.career-pipeline/`), local only |

The private search filters (work model, working hours) are personal research
criteria. They never appear in a public output, and they are not written
down in this repository, this file included.

## Building blocks

### 1. Profile source and LinkedIn suggestions
- One YAML file (`profile.yaml`) is the single source for projects, certificates
  and skills.
- The real profile lives in `~/.career-pipeline/`, next to the private config.
  The repository holds only a fictional test profile. Entries start as
  drafts (`confirmed: false`), and only confirmed entries reach a text.
- LinkedIn pinning is the owner's explicit choice (`pin: true`, at most 3).
  Recruiters filter by exact skill names, so the pipeline does not guess it
  from levels.
- Generated from it: the CV (PDF), README sections, and LinkedIn text suggestions
  for About, Projects, Skills and Certificates, plus an optional post draft.
- Triggers: a new project folder or release tag, or a new certificate in the YAML.
- Comparison: the owner pastes the current profile text, and the pipeline shows
  what is missing or out of date.
- **Language:** CV and LinkedIn texts are written in German for the German job
  market. Code, tests, file names and this repository stay in English.
- **Grounding check:** every skill, project, certificate and figure in a
  generated text must trace back to an entry in `profile.yaml`. One claim
  without a source fails the run, as in projects 12 and 13. The model words
  the text. It never adds facts.
- **No automated access to LinkedIn.** There is no official API for editing a
  profile, and automating it breaks the terms of use. The owner copies the
  texts over by hand.

### Application folder (private input)
- The owner's application folder is the second input next to `profile.yaml`.
  Its path lives in the private config only.
- **Read-only.** The pipeline never writes, moves or deletes anything there,
  as with `data/raw/` in project 10. Drafts go to `~/.career-pipeline/`.
- What it is used for:
  - the current CV and skills overview, as the starting point for `profile.yaml`
    (the owner confirms each entry before it counts)
  - past job descriptions, as extra evidence for the profile bottleneck: which
    requirements came up in ads the owner applied to
  - the rejected applications subfolder, kept as a separate group. A rejection has
    many causes, so it is reported as a pattern with its count, never as a cause.
- Nothing from the folder appears in a public output. The leak test checks for
  it too: company names from the folder count as private terms.

### 2. Job research (private)
- Search fields: AI workflows and automation, digitalisation, process
  optimisation, data analytics.
- Filters come from the private config only.
- First source: the Jobsuche API of the Bundesagentur für Arbeit. Further sources
  come later, behind the same interface.
- Work-model check: each ad is classified as *fully remote*, *hybrid*,
  *on-site* or *unclear*. Unclear ads are flagged, not discarded.
- Match score per ad, with the reason: which requirements are met and which are
  missing.

### 3. Two bottlenecks, measured separately
- **Profile bottleneck:** the requirement most often missing from the owner's
  profile in matching ads. Must-haves weigh more than nice-to-haves.
- **Market bottleneck:** skills in the four search fields that are in demand but
  hard to fill. Proxies are ads that stay online long or get reposted. The BA
  Engpassanalyse serves as context, not as the measure.
- **The overlap matters most:** a gap the owner has and the market struggles to
  fill.
- Every statement states its sample size. Counts are pooled over several runs,
  because a filtered segment is small and one week can mislead (see project 10:
  a two-day sample made two columns look constant).
- Counting happens in code, not in a language model.

### 4. Recommendation: certificate or project
- Always both options side by side: effort, cost, how many of the found ads each
  would cover, how visible it would be in the profile.
- A recommendation appears only once a gap has stayed stable over several runs.
- **Learning-goal brake:** one active learning goal at a time. Until the owner
  has decided on it or finished it, no new recommendation is issued. This stops
  the loop "new certificate → new gap → new certificate".

### 5. Learning loop: proposals, never silent changes
The research gets better from the owner's feedback, but every change waits
for the owner's approval. Without that gate it drifts, until it searches for
something else than what the owner wants.

- **What can learn:**
  - Match-score weights from the owner's ratings (*fits*, *does not fit*,
    *applied*). Outcomes from the application folder (invitation or rejection)
    are a weak extra signal.
  - New search terms: job titles found in good matches are proposed. They are
    never added on their own.
  - Work-model check: every correction becomes a fixed test case, as in
    project 12, so the same mistake cannot come back unnoticed.
  - Sources: a source with no matching ads over several runs is proposed for
    switch-off.
- **What never changes on its own:** the private filters, the search fields,
  the pipeline's own code and checks.
- **Safeguards:**
  - The weekly report has a section "Proposed adjustments", each with its
    reason and sample size.
  - Minimum sample size: weights only change after a fixed number of ratings
    (default 20).
  - Every adopted change is logged with its date and can be reverted.
  - Regression check: a change must not push a known good match out of the
    top results.
- **Supervised learning, honestly sized.** Two places in the loop are
  supervised learning problems, and they close the gap the portfolio has had
  since the IHK course (taught, no own project):
  - *Match score:* the owner's ratings are the labels. A classifier
    (logistic regression, then a decision tree for comparison) learns from
    features such as skill overlap, must-have coverage, field and work model.
  - *Work-model check:* the owner's corrections are the labels for a text
    classifier over the four classes.
  - Both are measured against the rule-based version as a baseline, with
    cross-validation and stated metrics (precision, recall, confusion matrix).
  - A model replaces the rule only after it beats the baseline on held-out
    data. Until then the rule stays in charge, and the report says why.
  - The data stays small (dozens of ratings, not thousands). The README says
    so, and the models stay simple and explainable for that reason.

## Data hygiene: no pile-up
The research runs every week, so it must not fill the disk or the owner's head.

- **Fixed file names, overwritten in place.** One current report, one set of
  CV and LinkedIn texts. No timestamped copies.
- **Ads are deduplicated** by their ID at the source. A repost updates the
  existing record; it does not create a new one.
- **Raw ads are pruned.** Full ad texts are kept for a set number of weeks
  (default 8, set in the private config). After that only the aggregate
  counts remain, which is all the bottleneck analysis needs.
- **History as one compact file**, one row per run with counts only, not one
  folder per run.
- **Ratings and the change log are kept.** They are small, and they are the
  training data and the audit trail.
- **The report has a size cap**: at most a fixed number of top matches
  (default 10), at most one recommendation.
- **A cleanup step ends every run**, and a test proves that two runs in a row
  leave the same set of files behind.

## Schedule
- Default: weekly. It can be set in the private config (weekly, fortnightly,
  monthly).
- **Runs as a local scheduled task in the Claude desktop app**, on the owner's
  machine. The task reads the private config from `~/.career-pipeline/` and
  writes its report there.
- **Not in GitHub Actions and not as a cloud routine.** The repository is
  public, and CI logs would expose the private filters. A cloud run would need
  the private config off the machine.
- The task prompt only points to the private config. It holds no filter values,
  so it can be shown or shared without leaking anything.
- The report contains new matching ads, the top matches with reasons, both
  bottlenecks with their trend, and at most one recommendation.

## Done when

### Step 1: Profile and public outputs
- [x] `profile.yaml` schema with a validating test
- [x] CV and LinkedIn suggestions generated from it, in German (CV as Markdown)
- [ ] CV as PDF
- [ ] Owner has confirmed the profile entries
- [x] **Grounding check:** a generated text with one claim not backed by
      `profile.yaml` fails the run. Covered by a test with a planted invented skill.
- [x] Profile comparison: pasted text vs. YAML → list of gaps
- [x] Application folder read-only (test: a write attempt is refused); its path
      and company names never appear in a public output
- [x] **Leak test:** every public output is checked against the terms in the
      private config. A single hit fails the run. A canary output with a planted
      private term must be caught.

### Step 2: Job research
- [ ] BA Jobsuche client behind an interface, tested offline with recorded responses
- [ ] Work-model classification with test cases for each of the four classes
- [ ] Match score with a stated reason per ad

### Step 3: Bottlenecks
- [ ] Run history stored locally, outside the repository
- [ ] Profile bottleneck and market bottleneck computed, each with its sample size
- [ ] Overlap reported separately

### Step 4: Recommendation
- [ ] Certificate and project shown side by side
- [ ] Stability threshold before a recommendation appears
- [ ] Learning-goal brake, covered by a test

### Step 5: Learning loop
- [ ] Ratings stored locally, outside the repository
- [ ] Proposals shown with reason and sample size, applied only after approval
- [ ] Minimum sample size enforced, covered by a test
- [ ] Change log with revert
- [ ] Regression check against known good matches
- [ ] Match-score classifier with cross-validation, compared against the rule baseline
- [ ] Work-model text classifier trained on the owner's corrections, same comparison
- [ ] A model takes over only after it beats the baseline; covered by a test

### Throughout
- [x] `python -m pytest` green, runs offline without an API key
- [ ] Schedule configurable, weekly by default
- [ ] Local scheduled task in the Claude desktop app set up; its prompt holds
      no private values
- [ ] README explains the decisions, not the theory
- [ ] Retention: raw ads pruned after the set weeks; two runs in a row leave the
      same file set (test)

## Not part of this round
- Automated applications, automated messages to recruiters
- Any write access to LinkedIn or other platforms
- Scraping of sites whose terms forbid it

## Decisions (fixed, not to be renegotiated)
- Private config and run data never enter the repository.
- The pipeline recommends, the owner decides.
- Counts in code. The language model only words texts and never adds facts.
- Runs locally as a Claude desktop scheduled task. Never in CI, never as a cloud routine.
- Code and repository in English. CV and LinkedIn texts in German.
- No pile-up: fixed file names, pruned raw data, counts kept, one report.
