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

- **Calibration run.** When the work unit *is* test authoring (new or changed spec cases), end the
  round with one targeted run of that spec and report it as **calibration**, never as gate evidence;
  the suite still runs once, at the freeze. A compile-only test round leaves capture devices,
  counters, "always passes" assertions and identifier collisions to be discovered at the gate.
- **Freeze expectation checklist** (when the brief is a freeze brief): a per-prefix table — one row
  per prefix in the filter, each with the previous run's count and the expected new cases — plus the
  new spec's own case count, the cases whose verdict needs runtime observation, and superseded logs
  moved out of the run directory with a marker.
- **Report labels.** `RESULT / CHANGES / DEVIATIONS / EVIDENCE / FORMAT / RISKS / NEXT / DETAIL`.

## Verifier (build & test)

`subagent_type: <verify-profile>` — pure execution: runs the single build + suite of the frozen tree
and reports it honestly.

```md
## OBJECTIVE
<one line: verify <change set> on the frozen tree>

## SCOPE
- allowed: run the build and the automation suite; mechanical compile fixes only
- forbidden: behaviour, design and test-expectation changes; writes outside the run dir

## CONSTRAINTS
- standards: `rem-test-completeness` for the gate, `rem-commit-workflow` for the exact commands
- environment: the build/test overlay (`rem-commit-workflow`, `local/build-test-and-commit.md`)
- delta over the standing template: <the case-plan pointer or tree state if it differs>

## ACCEPTANCE
- [ ] expected case count <N> per prefix observed and reconciled, <failing case names or "none">
- [ ] log cited by path

## REPORT
- run dir: <run-id, or "create one">
```

Role clauses:

- **Freeze expectation checklist.** Reconcile the runner's prefix counts against the brief's table,
  one row per prefix — never a single hand-counted total. For every difference, list the incremental
  case names and attribute each (this change / coexisting work-in-progress / undetermined). Name any
  case whose verdict needs runtime observation, and say explicitly when an earlier run's evidence was
  discarded as superseded (and why).
- **A 0-action build is not compile evidence.** When the build reports "target is up to date" (0
  actions), nothing compiled: cite the round the brief names as the one that actually compiled the
  tree and corroborate it with the artifact's hash or mtime, or force a rebuild. The suite run still
  stands.
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

- **Test-deliverable rounds** (the deliverable is tests): give a per-case non-vacuity verdict — would
  this case fail if the behaviour regressed? That is the finding class the round needs; an assertion
  that passes for the wrong reason is invisible to the compiler.
- **Cap the scope and state the priority.** A read-only audit has no write tool, so its report is
  the final message (`inline`) and the parent persists it. Name the files and dimensions that matter
  most and their order: a broad heavy audit is interrupted before it reports and has to be narrowed
  and re-dispatched.
- **Report labels.** `RESULT / SCOPE_REVIEWED / DIMENSIONS / FINDINGS / VERDICT / TEST_PLAN /
  NOT_COVERED / EVIDENCE / NEXT / DETAIL`.

## Git stage

`subagent_type: <git-profile>` — mechanical git execution: commits, history rewrite, submodule sync
and push, gated by the verified evidence.

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
- [ ] commit gate evidence cited, or a green verify run on exactly this tree named

## REPORT
- run dir: <run-id, or "create one">
```

Role clauses:

- **Split intent.** If the brief states a split, follow it exactly; otherwise decide it and return
  the full list (message + file set per commit) so the parent can veto.
- **No push without explicit instruction.** Publishing is a separate authorization; a brief that does
  not say "push" ends at the local commit and says so.
- **Report labels.** `RESULT / COMMITS / PUSHED / EVIDENCE / RISKS / NEXT / DETAIL`.
