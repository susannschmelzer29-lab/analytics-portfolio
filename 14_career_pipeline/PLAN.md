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
- [ ] `profile.yaml` schema with a validating test
- [ ] CV and LinkedIn suggestions generated from it, in German
- [ ] **Grounding check:** a generated text with one claim not backed by
      `profile.yaml` fails the run. Covered by a test with a planted invented skill.
- [ ] Profile comparison: pasted text vs. YAML → list of gaps
- [ ] Application folder read-only (test: a write attempt is refused); its path
      and company names never appear in a public output
- [ ] **Leak test:** every public output is checked against the terms in the
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

### Throughout
- [ ] `python -m pytest` green, runs offline without an API key
- [ ] Schedule configurable, weekly by default
- [ ] Local scheduled task in the Claude desktop app set up; its prompt holds
      no private values
- [ ] README explains the decisions, not the theory

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
