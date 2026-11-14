# Standing brief templates

Boilerplate for the four execution roles the harness delegates to. A brief is a **delta over these
templates**: the parent fills the placeholders with this round's facts and repeats only what the
round changes — the fixed blocks below are stated once here, not re-typed into every brief. The
commands, targets, configuration and test prefix come from the project's build/test overlay
(`rem-commit-workflow`, `local/build-test-and-commit.md`); copy them from there when filling a
template in, never from this file.

## Common blocks

Fixed in every role template:

- **Forbidden actions** — do not commit, push or rewrite history (the git stage owns that); do not
  run a disk scanner (`rem-no-disk-scanning`), search through the project's MCP server only and
  return `RESULT: blocked (rider-unavailable)` when it is down; do not touch files outside SCOPE or
  another unit's files; scratch goes to the OS temp dir (`rem-temp-files`) and the run directory
  receives only what a later reader needs.
- **Write set and resources** — SCOPE names the files (and the target) this unit may write, so the
  parent can run only disjoint units in parallel; sharing a file with a live unit is a dispatch defect,
  and an executor that needs anything outside the list stops and reports `blocked`.
- **Expected working set** — the brief pastes the expected `git status --short` output verbatim, not
  a counted total: a wrong count forces an avoidable round trip.
- **Report shape** — the role's fixed label lines below, no more than 40 lines, written in plain
  language for a human operator (no coined abbreviations; a term the operator did not introduce is
  explained the first time it appears). Full detail goes to `<run-dir>/report.md`; the final message
  is a summary plus pointers. A read-only profile has no write tool, so its brief asks for `inline`:
  the final message **is** the report and the parent persists it.
- **Run directory** — `<cwd>/.agents/runs/<run-id>/`; the executor appends to `state.md` and never
  creates a new run dir on `resume`.

## Implementer (authoring)

`subagent_type: <author-profile>` — implements one decided work unit and compiles the smallest target
containing the change.

```md
## OBJECTIVE
<one line: the work unit, verifiable>

## SCOPE
- allowed: <files / modules / symbols>
- forbidden: <files or units another executor owns>

## CONSTRAINTS
- standards: <skills for this unit, e.g. code authoring, tests, the domain skill>
- environment: commands and values from the build/test overlay (`rem-commit-workflow`,
  `local/build-test-and-commit.md`)
- delta over the standing template: <only what this round changes>

## ACCEPTANCE
- [ ] <checkable condition>

## REPORT
- run dir: <run-id, or "create one">
```

Role clauses:

- **The case is written here, run later.** A behaviour the round changes gets its case in the same
  commit (`rem-test-completeness` §4); which layer that case belongs in is §3c. Nothing defers as a
  description: what is left is a case that has never executed - one row in the plugin's unrun record
  naming why and the tier that runs it next (`rem-orchestration`, *Two records*) - and the report
  lists those rows as `UNRUN`. A red the round cannot show without running is marked
  `red not proven`.
- **Report labels.** `RESULT / CHANGES / DEVIATIONS / EVIDENCE / FORMAT / UNRUN / RISKS / NEXT / DETAIL`.

## Verifier (commit build and push gate)

`subagent_type: <verify-profile>` — pure execution in one of two uses: the commit gate **builds only**,
the push gate **builds and takes the range's single run**. It reports whatever it ran honestly and
never widens its own scope.

```md
## OBJECTIVE
<one line: build <change set> / build and run the push gate for <commit range>>

## SCOPE
- allowed: the build; at the push gate, one automation run at the brief's scope; mechanical compile fixes only
- forbidden: behaviour, design and test-expectation changes; writes outside the run dir

## CONSTRAINTS
- standards: `rem-commit-workflow` for the exact commands and the run scope, `rem-test-completeness` §3c for the layers
- environment: the build/test overlay (`rem-commit-workflow`, `local/build-test-and-commit.md`)
- delta over the standing template: <commit gate or push gate; the tree state; the prefix string>

## ACCEPTANCE
- [ ] build green, with its action count and the artifact's hash or mtime
- [ ] (push gate only) one run at the brief's scope - the core prefix string plus the prefixes the range touches - with <expected count per prefix> reconciled
- [ ] every recorded known red the run met, listed
- [ ] log cited by path

## REPORT
- run dir: <run-id, or "create one">
```

Role clauses:

- **Commit gate: one build, no suite.** The tree is the one the parent froze; a failure returns the
  work to iteration instead of starting a repair loop inside the gate.
- **Push gate: one build, one run, at the brief's scope.** The core layer is a generated
  `+StartsWith:` string from the project's layer table, never a guessed filter (`RunFilter Engine`
  pulls the engine's own suite; `SmokeFilter` on a spec kills every editor start). Never stack scopes
  - narrow, then module, then full - and a second run needs a stated reason: a changed tree, or a
  scope the first run could not reach. Which cases must run, and how an existing flat suite is brought
  into layers, is `references/test-layering.md` (classify, apply, measure) over the project's table.
- **The expectation checklist per prefix.** Give a table with one row per prefix in the run - the
  previous run's count and the expected new cases for that prefix - plus the new spec's own case
  count. Never hand-count a single total for the whole scope: the runner's `Found N` is the count,
  reported per prefix. Reconcile it per prefix and, on a mismatch, list the incremental case names and
  attribute each (this change / coexisting work-in-progress / undetermined). Name any case whose
  verdict needs runtime observation, and say explicitly when an earlier run's evidence was discarded
  as superseded (and why).
  Evidence: one session's hand-computed total disagreed with the run four times, and each miss cost
  a clarification round.
- **A 0-action build is not compile evidence.** When the build reports "target is up to date" (0
  actions), nothing compiled: cite the round the brief names as the one that actually compiled the
  tree and corroborate it with the artifact's hash or mtime, or force a rebuild. A suite run in the
  same session still stands.
- **Persist one authoritative log per stage**; a superseded copy leaves the run directory with a
  `superseded` marker.
- **Report labels.** `RESULT / BUILD / TESTS / EVIDENCE / MECHANICAL_FIXES / SUPERSEDED / RISKS /
  NEXT / DETAIL`.

## Reviewer (read-only audit)

`subagent_type: <review-profile>` — a read-only audit; it reports findings and never modifies files.

```md
## OBJECTIVE
<one line: audit <change set> across the review dimensions>

## SCOPE
- allowed: read the change set, its immediate blast radius, and the run-dir evidence
- forbidden: any file modification; reporting pre-existing unrelated debt

## CONSTRAINTS
- standards: <owning skill per dimension>
- delta over the standing template: <the dimensions that matter most this round>

## ACCEPTANCE
- [ ] every dimension has a verdict: pass | findings(file:line) | n/a + reason
- [ ] scope reviewed and scope not covered are both stated

## REPORT
- run dir: <run-id, or "inline" when no write tool is available>
```

Role clauses:

- **The cases, before the push gate's run,** get a per-case non-vacuity verdict - would this case
  fail if the behaviour regressed? That is the finding class the gate needs; an assertion that passes
  for the wrong reason is invisible to the compiler. Reconcile both ways: a case with no behaviour
  change behind it, or a behaviour change in the range with no case, is reported rather than waved
  through.
- **Cap the scope and state the priority.** A read-only audit has no write tool, so its report is
  the final message (`inline`) and the parent persists it. Name the files and dimensions that matter
  most and their order: a broad heavy audit is interrupted before it reports and has to be narrowed
  and re-dispatched.
- **Report labels.** `RESULT / SCOPE_REVIEWED / DIMENSIONS / FINDINGS / VERDICT / NON_VACUITY /
  NOT_COVERED / EVIDENCE / NEXT / DETAIL`.

## Git stage

`subagent_type: <git-profile>` — mechanical git execution: commits, history rewrite, submodule sync
and push, released only with the verified evidence.

```md
## OBJECTIVE
<one line: commit <change set> / push <refs>>

## SCOPE
- allowed: the named repositories and paths only
- forbidden: committing another author's work-in-progress; bundling unrelated changes

## CONSTRAINTS
- standards: `rem-commit-workflow` (and its `local/` overlay), `rem-rewrite-commit-history` for
  un-pushed history, the submodule skills when submodules move
- delta over the standing template: <the split intent, or "decide the split and report it">

## ACCEPTANCE
- [ ] one commit per change unit, `Type: short desc` in English with a bullet body
- [ ] the check's evidence cited, or a green verify run on exactly this tree named

## REPORT
- run dir: <run-id, or "create one">
```

Role clauses:

- **Split intent.** If the brief states a split, follow it exactly; otherwise decide it and return
  the full list (message + file set per commit) so the parent can veto.
- **No push without explicit instruction.** Publishing is a separate authorization; a brief that does
  not say "push" ends at the local commit and says so.
- **Report labels.** `RESULT / COMMITS / PUSHED / EVIDENCE / RISKS / NEXT / DETAIL`.
