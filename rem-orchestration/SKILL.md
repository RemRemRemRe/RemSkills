---
name: rem-orchestration
description: >
  Main-session orchestration policy for a project that uses this collection: delegate execution
  to subagents with self-contained briefs (background by default, never inheriting context), run
  the three-phase cadence - iteration that writes code and cases but runs nothing, a freeze that
  reviews the diff and builds once, and a push gate that runs the core test layer plus the prefixes
  the range touches; cut each round's slowest step by merging, caching or deferring it, and prefer
  events over polling when waiting. Use when planning, delegating, or sequencing work as the main
  session in such a project.
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
harness: few terms, no jargon and no coined shorthand ("verification run", not "VR"; "test scope",
not "scope"), any term the operator did not introduce explained the first time it appears, and the
language chosen by the writer - English, Chinese or a mix - for whatever carries the point best. Be
short - about a screenful - and delete any line the operator can neither learn from nor act on. A
claim without context is unusable - say what changed, why it matters, what it affects and what
happens next, prefer numbers, file paths and quoted evidence to adjectives, and point at the run
directory for detail. The hard rule lives in `orchestration-policy.md`; this section is the
procedure's restatement of it.

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
- **Writes serialize, reads parallelize** - the dispatch rules, per resource, live in
  *Concurrency and shared resources* below.
- **A read-only profile reports inline; the parent persists it.** Review, recon and grill profiles run
  without a write tool, so a brief that requires a report file produces none — ask for the report in
  the final message and let the parent write it into the run directory. Cap such a brief's scope and
  priority (which files and dimensions matter most, and in what order): a broad heavy audit gets
  interrupted before it produces findings and has to be narrowed and re-dispatched.
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

## Concurrency and shared resources

The rules below govern one session dispatching its own executors; sessions that share one project
coordinate through claims and leases (`rem-shared-resources`).

Parallelism is decided per **resource**, not per task. Before dispatching two units at once, name each
unit's **write set** (files, and the module or target it builds) and the shared resources it needs;
overlap on either means serialize.

- **Writers serialize per file and per directory.** Two executors never write the same file, the same
  generated-output directory or the same run directory; a brief that shares one with a live unit is a
  dispatch defect. When the overlap is unavoidable, run the units in sequence - the second starts from
  the first's result, never from a snapshot taken before it.
- **A reader of a file being written reads a torn tree.** Read-only analysis is valid on files no
  writer owns; a review or fact sheet of a unit still being edited is noise. Point readers at a
  finished unit, or at the tree once every writer has stopped.
- **One owner per shared resource.** The build (UBT), the automation suite, the editor or PIE session,
  the git index/worktree and history of one repository, and the IDE's MCP tools (formatter,
  breakpoints) are single-owner: a second run that needs one queues behind the first. A build started
  while another run writes sources proves nothing about either tree.
- **Verification reads a tree nobody is writing.** The freeze's build and the push gate's run
  start only after every writer has stopped; an earlier run is superseded, and a write after
  verification invalidates its evidence.
- **Git is one chain** - never two git executors on one repository, never a push during a rewrite.
- **Declare the lock in the brief.** SCOPE names the write set; an executor that needs a file or a
  resource outside it stops and reports `blocked` instead of taking it.
- **On discovered overlap, stop and re-plan.** Steer the writer to stop, or abort it; never let two
  writers resolve a conflict by writing over each other.

## Before the first edit

A repository that already holds uncommitted work is not a clean starting point. Before the first edit
of a unit, inventory the working tree per repository (submodules included) and settle every dirty
entry: commit it, record it as deferred with the reason, or declare it out of scope in writing. Until
that list exists, the commit stage degenerates into a negotiation over which dirty file belongs to
whose change - paid at the end, when separating the unit's own work is hardest. A dirty tree left alone
deliberately is fine; an unexamined one is not.

## Writing code, then the freeze

Iteration writes code and cases together; the build happens once, at the freeze, and cases run at the
push gate. Which layer a case belongs to, and what "full" means, live in `rem-test-completeness` §3c.

**Iteration writes cases and runs nothing.** A round may write or rewrite the cases for the behaviour
it changes, in the same commit as the code; a compile is the only execution evidence it may produce.
No suite, no single spec, no editor or PIE session opened to watch a behaviour. The reason is
measured, not stylistic: a run costs 30-40 s of editor startup before the first case (2026-11-14: a
176-case core run is ~70 s, half of it startup), so a run inside iteration spends the slowest step of
the whole loop on every round. The rule is revisited the day that startup comes down to compile time.

The price is stated rather than hidden: a case's capture, its counts and its identifiers are proven
only by executing, so a case that has never run is recorded in the plugin's *unrun cases* record
(below), and the first run that covers it owns making it pass.

**Freeze on a settled surface only.** The freeze runs when what the unit exposes has settled: its
contract is written down (signature, inputs and outputs, error behaviour), no later step in the plan
changes it, and the acceptance reads as one statement with no "for now". The parent decides this and
states it in the brief - only the parent knows the coming steps, so the executor never judges it
alone. Until then the round stays in iteration: compile, append intent lines, write no spec, no case
and no deliverable doc (working records are written as the need appears).

- **Split by stability, not by module.** Inside one unit, freeze and commit the settled leaves first -
  pure functions, data structures, algorithms, naming and path conventions - and write their cases in
  the same round as the code, while the surface is still in the author's hands. The volatile layer
  above them - orchestration, lifecycle, wiring - stays in iteration.
- **Cap the unrun backlog.** No more than ~10 unrun cases per plugin before a run is scheduled at the
  push gate, and never two rounds of reworked cases with no run between them: a case that never
  executed is not evidence, and a pile of them hides which one is wrong.
- **Discarding is explicit.** A dropped direction takes its cases and intent lines with the code;
  record what was dropped, and why, in `state.md`.
- **TDD survives as two facts.** The intent line is written *before* the code, and a change to
  existing behaviour writes its case against the pre-change tree wherever red is visible without a run
  (a pure addition only has to pass "could this assertion ever fail", `rem-test-completeness` §3b). A
  fix whose red cannot be seen without executing says so in the unrun record and marks the case
  `red not proven`. Documentation follows the same rule: a deliverable doc is written for a settled
  surface only, as soon as it settles; the freeze sweeps what is missing.

1. **Iteration** - per work unit: edit, compile the affected target, write or update the unit's cases
   in the same commit, and record test intent in `<run-dir>/test-intent.md` as one
   `<prefix> | trigger -> assertion` line per behaviour. No suite run, no docs sweep.
2. **Freeze** - declared by the parent once the surface has settled: review the accumulated diff for
   code quality, sweep the docs, take one full build, commit. The build is the commit's evidence.
3. **Push gate** - operator-triggered, possibly in another session: the core layer plus every prefix
   the range touches (`rem-test-completeness` §3c names the tiers), one run, reported as the range's
   evidence. The cases it covers become proven; the rest stay in the unrun record.

Three rules bind that sequence:

- **A local commit may carry unrun cases; a push may not.** A case written and never executed is one
  row in the plugin's *unrun cases* record and is named in the commit that adds it; the push gate's
  run is what turns them into evidence. Externally visible behaviour and bug fixes are written in the
  commit's own round (`rem-test-completeness` §4).
- **Size change sets by verification unit.** Production fixes, new tests, adjacent utility fixes and
  test-infrastructure refactors belong to separate units, because one run re-verifies every change in
  its scope. Two independent, low-risk units over disjoint files may share one gate. Apply the
  review's severity ladder: blocking and major findings are fixed in the round, minor and elegance
  findings go to a backlog list.
- **The push gate is its own session.** The operator opens it and names its scope; it may run in
  another session, after the commit. Its procedure - scope, build, one run - is owned by
  `rem-commit-workflow`.

## Two records, not a ledger

A deferred *description* rots: by the time a later session reads "the warning is reported once", the
code may report it four times - the row was never wrong about intent, only stale about code. So
nothing defers as a description any more. Two small local records replace the ledger, under
`<cwd>/.agents/test-debt/` (git-ignored):

| record | one row per | fields |
|---|---|---|
| unrun cases | a case that exists and has never been executed | `case | why it has not run | the tier that runs it next` |
| manual checks | a behaviour no headless case can reach | `behaviour | the procedure that checks it | performed / owed` |

- A behaviour with no case gets its case in the round that changes it; it does not enter a record.
- A **known red** is an unrun row whose reason is `red`, plus an owner and a deadline. A non-core known
  red with both does not block the gate; a core one does. The gate's run must list every known red it
  met, so "no new failures" stays checkable.
- Two classes never defer past the commit: externally visible behaviour and bug fixes
  (`rem-test-completeness` §4).
- The records are local by decision - losing the machine loses them. Next to them, `case-renames.md`
  maps every case name this project ever renamed, dropped or merged, so a record that cites an old name
  stays resolvable.
- The layer each case belongs to, and the prefix string the gate runs, live in
  `rem-orchestration/local/test-layers.md` (project data, not this skill).

## Fewest cycles

The cost that matters is **cycles**, not keystrokes: one round trip costs more than a slightly larger
first attempt.

- **Cheap evidence first, expensive evidence last** - a compile before a build, a build before the
  suite; never run the expensive one to answer what the cheap one answers.
- **Batch related work** - one compile per coherent batch, one suite per unchanged tree, one doc
  sweep per unit. A compile per file multiplies the cheapest step; a suite per fix multiplies the
  dearest.
- **Reuse evidence** - an unchanged tree keeps its evidence (hash/mtime); only the new bytes need a
  new run.
- **Parallelize what shares no file** - writers serialize per file; reads, disjoint repositories and
  the doc pass proceed alongside.
- **Script repeated edits** - past ~50 sites a scripted transform with an inverse-diff proof is
  cheaper, and it removes the per-site review round.
- **Make the brief complete** - a missing constraint costs a round trip; quoting the expected working
  set costs one line.
- **Record what a round cost** - compile count, suite runs and round trips in `state.md`; you can
  only cut what you measured.

### Finding the slow step

Every round has one step that dominates its wall-clock time, and cutting *that* step is the only
change that shortens the next round. So every round ends with one line in `state.md`, written by
whoever ran the round and without being asked: the slowest step, and what it cost. Typical candidates
here are the full build, the automation suite, an editor or PIE session, an IDE round trip, asset
regeneration, and a subagent round trip (whose fixed brief/report cost is the slow part, not the
work).

Slow means measured wall-clock time in this round, not expensive in principle. The next round then
gives that step one of three treatments:

| Treatment | When it applies |
|---|---|
| **Merge** | two steps need the same expensive input: one compile for a batch of edits, one editor session for several assets, one suite run for several prefixes |
| **Cache** | the result stays valid while its input is unchanged: a build's artifact hash/mtime, a spec run's counts, a finished review of a hunk |
| **Defer** | the step is only needed once the surface settles or the operator asks for it: the freeze's build, the push gate's run (deferred to its own operator-triggered session), the docs sweep, a review pass - deferred with a record, never silently |

A slow step that runs twice inside one round was mis-ordered: its inputs were not complete when it
started, so fix the order instead of repeating the run. Two slow steps in a row over an unchanged
tree mean the loop has stalled - stop and re-plan rather than iterate again.

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
- **The parent keeps `plan.md`.** One line per work unit - is the surface settled, has the freeze
  run, how many cases are unrun - appended by the parent; executors may read it when their brief
  points there.
- `resume` continues the same child session and the same run directory: append to
  `state.md`, never create a new run dir.

## Environment quirks

Process-level invocation quirks belong to the project's build/test overlay (`rem-commit-workflow`,
`local/build-test-and-commit.md`, which lists the commands), not to this skill - so the skill stays
portable and the values sit next to the commands they change. Two shapes recur: invoking a Windows
batch builder from a POSIX shell needs its path conversion disabled (a quoted
`-project="…"`/`-ExecCmds="…"` line arrives with literal backslashes and fails at argument parsing),
and a file must be re-read after a formatter run because a stale editor buffer can overwrite it from
older content — re-reading first is not enough: never format a file the IDE still holds unsaved
edits for, and compare the file's hash before and after every IDE call. The brief points at the
overlay file; it never copies the commands into itself.
Harness-level operational facts of the current installation (model/MCP configuration, context
cost) live in `local/pi-harness.md` under the same split: values there, portable rules here.

Two scheduling rules are harness-general and belong here too:

- **Tool calls issued in one response may run in parallel and out of order.** Never rely on the
  order of calls within a single response - a write can be overtaken by a read or edit issued in
  the same message. A follow-up that depends on an earlier call's result belongs in a later turn.
- **A tool call that times out may already have executed.** Inspect the target's state before
  retrying: the timed-out attempt can have completed (a saved file, an opened dialog), and a blind
  retry then duplicates the effect - a duplicated multi-GB project, for example.

## Checklist

- [ ] Decisions, constraints and acceptance criteria stayed in the main session; raw material went to executors and run dirs
- [ ] Run dirs hold only what a later reader needs — one-off generators, patches and message files stayed in temp (`rem-temp-files`)
- [ ] Every brief was self-contained (no inherited context) and named its acceptance criteria
- [ ] Execution ran in the background unless the same turn needed the result
- [ ] Iteration wrote cases with the code and ran nothing; the freeze swept the docs and took one full build; the suite ran only at the push gate
- [ ] Every unit that reached the freeze had a settled surface (contract written, no planned change, no "for now"); work that had not settled stayed in iteration and obeyed the ~10-case unrun ceiling
- [ ] Every case written and never executed became one unrun row naming the tier that runs it; externally visible behaviour and bug fixes carried their case in the commit instead
- [ ] A regression case whose red could not be shown without a run was marked `red not proven`, not asserted as proven
- [ ] A 0-action ("target is up to date") build was not accepted as compile evidence — the evidence names the round that actually compiled the tree, with its artifact hash/mtime as corroboration
- [ ] A tree change after the freeze's build got a re-run covering the new bytes, or a stated inert-delta exemption backed by a calibration run covering the changed spec
- [ ] No polling waits, no `wait: true` blocking; completion judged from the run directory
- [ ] Non-compiled documentation ran in parallel with the code work where no file was shared
- [ ] Each round named its slowest step in `state.md` and merged, cached or deferred it; no expensive step ran twice inside one round
- [ ] Mechanical sweeps above ~50 sites used a scripted transform with an inverse-diff proof
- [ ] Every brief carried only its delta over the standing template and quoted the expected working set verbatim
- [ ] Each item crossing a module/DLL/lifecycle/build boundary got a one-line feasibility check before dispatch
- [ ] A rename, drop or merge of a case produced one row in `case-renames.md`, generated from the before/after case names rather than hand-written
- [ ] The push gate's run used the generated prefix string - not `RunFilter Engine`, and never a spec carrying `SmokeFilter`
- [ ] Test deliverables got their focused review before the push gate's run
- [ ] Change sets were sized by verification unit; blocking/major findings fixed in the round, minor/elegance listed for backlog
- [ ] The push gate's brief gave a per-prefix expected-count table; the run reconciled it per prefix and attributed every delta
- [ ] Read-only profiles (review/recon/grill) reported inline, with a capped scope and priority; the parent persisted the report
- [ ] The run directory holds one authoritative log per stage; superseded logs moved out with a marker
- [ ] Operator-facing text was plain, context-bearing and free of coined shorthand
- [ ] Every pre-existing dirty entry was committed, deferred with a record, or declared out of scope before the first edit
