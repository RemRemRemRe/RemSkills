---
name: rem-orchestration
description: >
  Main-session orchestration policy for a project that uses this collection: delegate execution
  to subagents with self-contained briefs (background by default, never inheriting context), run
  the iteration/freeze cadence - compile-only iteration, one build + suite at the freeze point -
  and prefer events over polling when waiting. Use when planning, delegating, or sequencing work
  as the main session in such a project.
metadata:
  category: workflow
  trigger: manual
---

# Main-Session Orchestration

The main session is the decision ledger; executors are its hands. Keep the goals,
constraints, acceptance criteria and pointers; push raw material (diffs, logs, file
bodies) into subagents and run directories. The project's short hard rules live in its
agent context file, which points here for the procedure.

## Talking to the user

Every reply and every subagent report the operator reads is written for a person, not for the
harness: the operator's own language, plain words, no jargon and no coined shorthand ("verification
run", not "VR"; "test scope", not "scope"), and any term the operator did not introduce explained
the first time it appears. A claim without context is unusable - say what changed, why it matters,
what it affects and what happens next, prefer numbers, file paths and quoted evidence to adjectives,
keep it to about a screenful, and point at the run directory for detail. The hard rule lives in
`orchestration-policy.md`; this section is the procedure's restatement of it.

## Delegation

- **Delegate execution, keep decisions.** A unit whose raw output exceeds ~10k tokens, or
  whose process is open-ended (build/fix loops, debugging, batch refactors, repo-wide
  search), belongs to a subagent. Small, high-coupling steps stay in the main session - the
  brief/report fixed cost makes delegation a net loss there.
- **Check feasibility before dispatch.** Any brief item that crosses a module boundary, a
  DLL/ABI boundary, a lifecycle order or a build configuration gets a one-line feasibility
  check by the parent against the design record *before* it is delegated; an item that
  actually needs a design decision is split out as a decision, not handed to an executor.
- **Briefs are self-contained.** Objective / scope (allowed + forbidden) / constraints /
  acceptance / report pointer. Never rely on inherited context; a subagent that cannot
  start without it is a brief defect.
- **Briefs are a template plus a delta.** The boilerplate - forbidden actions, scope, build
  command, report shape - is the standing template in `references/brief-templates.md`; a
  brief repeats only what this round changes.
- **Quote the expected working set.** The brief pastes the expected `git status --short`
  output verbatim instead of a counted total: a wrong count forces an avoidable round trip.
- **Background by default.** Pass `run_in_background: false` only when the next decision
  needs the result in the same turn and nothing else can run meanwhile. Parallelism comes
  from issuing several Agent calls in one message, not from the background flag.
- **Writes serialize, reads parallelize.** Never run two writers over the same file. A running
  writer blocks only the files it owns, so documentation that is not a build input, the next
  stage's brief, a disjoint repository and read-only analysis of finished material all proceed
  alongside it; only a read of a *frozen* tree (the verification of a change set) must wait for
  every writer to stop.
- **Mechanical sweeps are scripted, not hand-edited.** Past roughly 50 sites of one repeated
  change, derive the explicit file list first (page the search until the set is complete; a
  silently truncated result is the classic failure), transform with a script that preserves bytes
  outside the change, prove it by inverting the transform and diffing, have the executor validate
  the staged diff file by file, and have the review cover the non-mechanical sites exactly plus a
  sample of the mechanical ones. Evidence: one run spent its whole budget on a 126-site sweep
  before making a single edit, while the scripted version of the same shape finished 232 sites in
  one pass.
- **No profile turn cap.** `max_turns` is a per-call kill switch: at the limit the child
  gets one wrap-up turn and is then aborted (the run is still reported as completed), so
  read the run directory instead of assuming a report exists.
- **Verify from artifacts.** A run's outcome is its run directory (`report.md`, logs) or the
  child session's final message - never "it is still running".

## Iteration and freeze

Iteration is code-only; the expensive gates run once, at the freeze point.

1. **Iteration** - per work unit: edit, compile the affected target, record test intent in
   `<run-dir>/test-intent.md` as one `trigger -> assertion` line per behaviour. No specs,
   no suite run, no docs sweep.
2. **Freeze review** - one review pass over the accumulated diff produces the case plan:
   the existing-case index plus the missing or updated cases.
3. **Test authoring** - write the cases from that plan. Whichever executor writes new or changed
   cases ends its round with one *targeted* run of that spec, reported as **calibration**, never as
   gate evidence - the one-run-at-freeze rule governs the *suite*, not this run. Expectation
   bookkeeping (how many times a message is recorded, which record a pattern claims), capture
   devices, counters, "always passes" assertions and identifier collisions are only visible by
   executing, so a compile-only test round pushes them into the freeze and costs a red gate plus
   extra rounds. Evidence: a wrong declaration turned into a red gate, a resumed authoring round and
   a second full build plus suite.
4. **Verify** - one build plus one suite run, at the scope decided up front, on the frozen tree.
   A build that reports "target is up to date" (**0 actions**) is **not** compiler evidence: nothing
   compiled. When that happens, take the compile evidence from the round that actually compiled the
   tree (name it in the brief), or require a forced rebuild; the suite run still stands.
5. **Docs, then git** - batch the documentation obligations once, then commit. When the tree
   did not change after verify, the commit stage checks the recorded evidence instead of
   re-running. A bug fix proves its regression case by temporarily reverting the fix at the
   freeze point. A change to the tree **after** the freeze needs a re-run that covers the new
   bytes; a delta that is provably inert (comments only) may be exempted when a calibration run
   covers the one changed spec — and the exemption's reasoning is stated in the brief, never
   left implicit.

Three rules bind that sequence:

- **Review test deliverables before the freeze.** When the round's deliverable is tests, run the
  focused review of the new/changed test files before the freeze gate, in parallel with the
  calibration run. The dominant defect class there - an assertion that passes for the wrong reason -
  is invisible to the compiler and to a compile-only round.
- **Size change sets by verification unit.** Production fixes, new tests, adjacent utility fixes and
  test-infrastructure refactors belong to separate units, because one red gate re-verifies every
  change in the unit. Apply the review's severity ladder: blocking and major findings are fixed in
  the round, minor and elegance findings go to a backlog list.
- **The freeze brief states the expectation.** Give the expected case count (the previous run's
  count plus the new cases), name any case whose signal needs runtime observation, and require the
  executor to report superseded runs explicitly.

## Waiting

- Prefer events over polling: background subagents wake the session on completion; a long
  external process is run as a blocking call with a sufficient tool timeout.
- Do not use `get_subagent_result(wait: true)` as a blocking wait, and do not sleep-poll. If
  a run looks stuck, read its run directory or child session for a final message before
  waiting again; report a genuine stall to the user.
- 15 s is the pragmatic ceiling for a poll interval; use a better signal when one exists.

## Artifacts

- **Temp first** (`rem-temp-files`): one-shot generators, patches, message files and
  superseded logs stay in a unique temp dir. `<cwd>/.agents/runs/<run-id>/` receives only
  what a later reader needs — `brief.md` (parent), `state.md`, `test-intent.md`, the
  authoritative logs and `report.md` (executor, append-only); the final message stays a
  bounded summary with pointers.
- **One authoritative log per stage.** A superseded run's logs move out of the run directory
  with a "superseded" marker; the run directory holds the logs the report cites.
- `resume` continues the same child session and the same run directory: append to
  `state.md`, never create a new run dir.

## Environment quirks

Process-level invocation quirks belong to the project's build/test overlay (`rem-commit-workflow`,
`local/build-test-and-commit.md`, which lists the commands), not to this skill - so the skill stays
portable and the values sit next to the commands they change. Two shapes recur: invoking a Windows
batch builder from a POSIX shell needs its path conversion disabled (a quoted
`-project="…"`/`-ExecCmds="…"` line arrives with literal backslashes and fails at argument parsing),
and a file must be re-read after a formatter run because a stale editor buffer can overwrite it from
older content. The brief points at the overlay file; it never copies the commands into itself.

## Checklist

- [ ] Decisions, constraints and acceptance criteria stayed in the main session; raw material went to executors and run dirs
- [ ] Run dirs hold only what a later reader needs — one-off generators, patches and message files stayed in temp (`rem-temp-files`)
- [ ] Every brief was self-contained (no inherited context) and named its acceptance criteria
- [ ] Execution ran in the background unless the same turn needed the result
- [ ] Iteration stayed compile-only; specs, the build + suite and docs ran once at the freeze point
- [ ] A 0-action ("target is up to date") build was not accepted as compile evidence — the evidence names the round that actually compiled the tree
- [ ] A post-freeze tree change got a re-run covering the new bytes, or a stated inert-delta exemption backed by a calibration run covering the changed spec
- [ ] No polling waits, no `wait: true` blocking; completion judged from the run directory
- [ ] Non-compiled documentation ran in parallel with the code work where no file was shared
- [ ] Mechanical sweeps above ~50 sites used a scripted transform with an inverse-diff proof
- [ ] Every brief carried only its delta over the standing template and quoted the expected working set verbatim
- [ ] Each item crossing a module/DLL/lifecycle/build boundary got a one-line feasibility check before dispatch
- [ ] A test-authoring round ended with one targeted calibration run, reported as calibration rather than gate evidence
- [ ] Test deliverables got their focused review before the freeze gate
- [ ] Change sets were sized by verification unit; blocking/major findings fixed in the round, minor/elegance listed for backlog
- [ ] The freeze brief stated the expected case count, the cases needing runtime observation, and the superseded-run requirement
- [ ] The run directory holds one authoritative log per stage; superseded logs moved out with a marker
- [ ] Operator-facing text was plain, context-bearing and free of coined shorthand
